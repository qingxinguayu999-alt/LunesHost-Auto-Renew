# Lunes Host Auto Keep-Alive

通过 GitHub Actions 定期登录 Lunes Host 的 Betadash，帮助已获许可的免费服务器保持活跃。

> **重要：** Lunes Host 的服务条款限制未经明确许可的自动化使用。请先获得 Lunes Host 的许可，再启用本项目。网站规则或页面结构改变后，本项目可能失效。

## 隐私设计

- 邮箱和密码只保存在每位使用者自己仓库的 GitHub Actions Secrets 中。
- 项目不会把账号写进代码、提交记录或 Actions 配置。
- 不保存 Cookie、浏览器状态、网页源码、截图或运行产物。
- 日志不会输出邮箱、密码、服务器 UUID、地址或页面内容。
- Telegram Bot Token 和 Chat ID 也只从 Secrets 读取，不写入通知或日志。
- Fork 之间的 Secrets 完全独立，原仓库维护者无法读取你的 Secrets。

## 使用方法

1. Fork 本仓库，或使用本仓库文件创建自己的仓库。
2. 打开你的仓库：`Settings` → `Secrets and variables` → `Actions`。
3. 添加两个 Repository secrets：

   | Secret 名称 | 内容 |
   | --- | --- |
   | `LUNES_EMAIL` | Betadash 登录邮箱 |
   | `LUNES_PASSWORD` | Betadash 登录密码 |
   | `TG_BOT_TOKEN` | 可选：Telegram Bot Token |
   | `TG_CHAT_ID` | 可选：接收通知的用户或群组 ID |

4. 打开 `Actions` → `Lunes Host keep-alive` → `Run workflow`，先手动测试一次。
5. 测试成功后保留定时任务。默认每周三 03:17 UTC 执行一次，低于页面提示的 15 天期限。

`TG_BOT_TOKEN` 和 `TG_CHAT_ID` 必须同时配置。两项都不配置时，续期功能照常运行但不会发送通知；只配置其中一项时，日志会提示通知未启用。

GitHub 默认不会把 Secrets 复制到 Fork；每个使用者必须在自己的仓库中单独添加。公开仓库长时间没有活动时，GitHub 可能停用定时工作流，请定期查看 Actions 状态。

## 成功与失败

成功日志只显示：

```text
Success: Lunes dashboard login was verified.
```

登录失败时，工作流会退出并标红，但不会上传截图或页面内容。请重新检查 Secrets，或确认 Lunes 是否更改了登录页面。

脚本以 Betadash 的受保护页面和登录表单状态确认结果，不依赖单一语言的按钮文字，因此页面翻译或文字调整不会把成功登录误报为失败。

配置 Telegram 后，成功和失败都会收到通知。通知只包含运行结果和 UTC 时间，不包含账号或服务器信息；Telegram 暂时不可用不会改变续期任务本身的成功或失败状态。

## 本地运行

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
LUNES_EMAIL="your-email" LUNES_PASSWORD="your-password" python renew.py
```

请勿把真实凭据写入脚本、`.env` 文件或 Issue。

## 安全与责任

本项目不是 Lunes Host 官方项目。使用者应自行确认自动化符合 Lunes Host 的最新规则，并对账号及服务器数据负责。发现安全问题时请按照 [SECURITY.md](SECURITY.md) 私下报告。

## License

[MIT](LICENSE)
