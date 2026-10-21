#!/usr/bin/env bash
# Run from the host SSH terminal. The current Codex sandbox cannot write .git
# or create/connect to the tmux socket.
set -Eeuo pipefail
umask 077

fail() { printf 'Lỗi: %s\n' "$*" >&2; exit 1; }

# Gitignore does not protect previously tracked files. Stop before staging or
# committing if private/runtime data has already been tracked.
check_tracked_files() {
    local tracked_name
    while IFS= read -r -d '' tracked_name; do
        case "$tracked_name" in
            data/*.db*|data/admin-auth.json|data/initial-admin-password.txt|data/ai-settings.json|\
            .env|.env.*|.aws/*|.codex/*|backups/*|logs/*|tools/*|models/ollama/*|.venv/*|.worktrees/*|\
            application.tar.gz|reports/*.zip)
                [[ "$tracked_name" == '.env.example' ]] && continue
                fail "File riêng tư/runtime hoặc gói lưu trữ đang được Git theo dõi: $tracked_name. Hãy kiểm tra trước khi commit."
                ;;
        esac
    done < <(git ls-files -z)
}

if [[ "${1:-}" == '--worker' ]]; then
    [[ $# == 3 ]] || fail 'Thiếu tham số worker.'
    task_worktree=$2
    task_logs=$3
    cd "$task_worktree"
    exec > >(tee -a "$task_logs/run.log") 2>&1
    trap 'task_exit=$?; printf "%s\n" "$task_exit" > "$task_logs/exit-code"; if (( task_exit != 0 )); then printf "failed (exit %s)\n" "$task_exit" > "$task_logs/status"; fi' EXIT
    printf 'running\n' > "$task_logs/status"
    printf 'Bắt đầu: %s\nWorktree: %s\n' "$(date -Is)" "$task_worktree"
    codex --no-daemon --ask-for-approval never exec \
        --sandbox workspace-write --cd "$task_worktree" --color never \
        --output-last-message "$task_logs/final.md" - \
        < "$task_worktree/prompts/report-alignment.md"

    [[ -f reports/report-alignment-ready.txt ]] || fail "Codex chưa bàn giao triển khai; xem $task_logs/final.md"
    [[ "$(cat reports/report-alignment-ready.txt)" == 'ready' ]] || fail 'Marker bàn giao không hợp lệ.'
    printf 'Chạy lại kiểm thử trước khi commit...\n'
    timeout 300 .venv/bin/python -m pytest tests -q
    printf 'complete\n' > reports/report-alignment-complete.txt
    check_tracked_files
    git add -A
    check_tracked_files
    git diff --cached --check
    if ! git diff --cached --quiet; then
        git commit -m 'Align intent classification and experiments with research report'
    fi
    git log -1 --format='%h %s' > "$task_logs/result-commit.txt"
    printf 'complete\n' > "$task_logs/status"
    printf 'Hoàn tất: %s\n' "$(date -Is)"
    exit 0
fi

[[ $# == 0 ]] || fail 'Cách dùng: bash scripts/start_report_alignment.sh'
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$task_root"
for task_program in git tmux codex flock tee timeout; do
    command -v "$task_program" >/dev/null || fail "Chưa có lệnh $task_program."
done
[[ -x .venv/bin/python ]] || fail 'Thiếu .venv/bin/python.'
[[ -f prompts/report-alignment.md ]] || fail 'Thiếu prompt bàn giao.'
.venv/bin/python -c 'import pytest, fastapi, sklearn, httpx' || fail 'Môi trường Python chưa đủ thư viện.'
tmux -V >/dev/null
task_guard="$task_root/logs/report-alignment.lock"
mkdir -p "$task_root/logs"
exec 9>"$task_guard"
flock -n 9 || fail 'Một lần khởi chạy khác đang hoạt động.'
# Do not mistake a parent repository for this project.
if git rev-parse --show-toplevel >/dev/null 2>&1; then
    [[ "$(git rev-parse --show-toplevel)" == "$task_root" ]] || fail 'Dự án đang nằm trong Git repo cha; dừng để tránh commit nhầm.'
else
    git init -b main
fi
git var GIT_AUTHOR_IDENT >/dev/null 2>&1 || fail 'Chưa cấu hình Git author. Chạy git config user.name và git config user.email với thông tin của bạn rồi chạy lại.'
git var GIT_COMMITTER_IDENT >/dev/null 2>&1 || fail 'Chưa cấu hình Git committer.'
check_tracked_files
[[ -z "$(git diff --name-only --diff-filter=U)" ]] || fail 'Repo còn xung đột Git chưa được giải quyết.'

task_stamp=$(date +%Y%m%d-%H%M%S)
task_branch="report-alignment-$task_stamp"
task_session="student-report-$task_stamp"
task_worktree="$task_root/.worktrees/$task_branch"
task_logs="$task_root/logs/$task_session"
mkdir -p "$task_logs"
task_pending="$task_root/logs/report-alignment-session-pending"
if [[ -f "$task_pending" ]]; then
    task_previous=$(cat "$task_pending")
    if tmux has-session -t "=$task_previous" 2>/dev/null; then
        fail "Phiên $task_previous vẫn còn tồn tại; kiểm tra bằng tmux attach -t $task_previous."
    fi
fi
# Start the server before touching Git; preserve the tmux pane after the job
# exits, so a quick error is still inspectable after reconnecting.
tmux new-session -d -s "$task_session" -c "$task_root"
tmux set-option -w -t "$task_session" remain-on-exit on
printf '%s\n' "$task_session" > "$task_pending"

git add -A
check_tracked_files
if ! git diff --cached --quiet; then
    git commit -m 'Snapshot HaUI Assist before report alignment'
elif ! git rev-parse --verify HEAD >/dev/null 2>&1; then
    fail 'Không có nội dung để tạo snapshot.'
else
    git commit --allow-empty -m 'Snapshot HaUI Assist before report alignment'
fi
git rev-parse HEAD > "$task_logs/baseline-commit.txt"
git worktree add -b "$task_branch" "$task_worktree" HEAD
ln -s "$task_root/.venv" "$task_worktree/.venv"
printf '%s\n' "$task_branch" > "$task_logs/branch"
printf '%s\n' "$task_worktree" > "$task_logs/worktree"
printf 'starting\n' > "$task_logs/status"
printf -v task_command 'bash %q --worker %q %q' \
    "$task_worktree/scripts/start_report_alignment.sh" "$task_worktree" "$task_logs"
tmux respawn-pane -k -t "$task_session:0.0" "$task_command"
printf '%s\n' "$task_session" > "$task_root/logs/report-alignment-session"
printf '%s\n' "$task_logs" > "$task_root/logs/report-alignment-latest"
printf '\nĐã tạo snapshot: %s\nNhánh: %s\nWorktree: %s\n' \
    "$(cat "$task_logs/baseline-commit.txt")" "$task_branch" "$task_worktree"
printf 'Phiên tmux: %s\nLog: %s\n' "$task_session" "$task_logs"
printf '\nXem phiên: tmux attach -t %s\n' "$task_session"
printf 'Rời tmux và giữ tác vụ chạy: Ctrl+B rồi D. Sau đó có thể ngắt SSH.\n'
printf 'Xem trạng thái: cat %q/status\n' "$task_logs"
printf 'Xem kết quả cuối: cat %q/final.md\n' "$task_logs"
