# Changelog

## v0.2.2 (2026-04-20)

- README 全中文化
- 项目结构精简，删除未接入的 enrich 模块和冗余文档
- 清理仓库元数据

## v0.2.1 (2026-04-20)

- **Install scripts**: one-shot `install.ps1` (Windows) and `install.sh` (Linux/macOS) with Bark key / device name / emoji params
- **Uninstall scripts**: `uninstall.ps1` / `uninstall.sh` remove hooks and env from `settings.json`
- **Public README**: rewritten for first-time users, zero personal info
- **Secret scanner**: `scripts/check_secrets.py` + CI workflow + optional pre-commit hook
- **Shared JSON patcher**: `scripts/_patch_settings.py` (upsert hooks & env, idempotent, dry-run)
- **Tests**: `test_patch_settings.py` (5 cases) and `test_check_secrets.py` (2 cases)
- **CI**: GitHub Actions matrix (ubuntu + windows, python 3.9/3.11/3.12)

## v0.2.0 (2026-04-17)

- Single-file notify core (`ccbell/notify.py`) — config via env vars only
- `stop_reason` emoji differentiation (error / interrupt / truncation)
- URL-encoding for non-ASCII group names
- Path sanitization (home dirs, private IPs)

## v0.1.0 (2026-04-16)

- Initial skeleton: dispatch.py + hook entry + dry-run mode
