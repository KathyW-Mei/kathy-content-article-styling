# 版本说明

## 版本策略

- 文档采用语义化版本（SemVer）。
- 重大结构调整记为主版本；功能新增记为次版本；修复记为补丁版本。
- 版本信息仅记录在本文件中，其余文档不含版本标签。

---

## 当前版本

### v2.1

**发布日期**：2026-01-29

**变更摘要**：
- 封面风格与主图风格解耦，可独立选择
- `styles.json` 分离为 `cover_styles` 与 `main_styles`
- Step01 增加两轮风格选择（封面 / 主图）

**兼容性说明**：
- 旧版 `styles.json`（单一 `styles` 结构）不再兼容
- 旧版 `style_id` 仍可作为回退字段，但建议迁移到 `cover_style_id` / `main_style_id`

**升级指引**：
1. 将 `reference/images/styles.json` 更新为 `cover_styles` / `main_styles` 结构
2. 在 `state/config.json` 中写入 `cover_style_id` 与 `main_style_id`
3. 重新运行 Step01 生成新配置

---

## 历史版本

### v2.0

**发布日期**：2026-01-xx

**变更摘要**：
- 固定风格垫图模式
- 封面 + 主图流程稳定

