# 上游开放 issue 检查记录

检查日期：2026-10-12（Asia/Shanghai）。上游基线：`5c71562`，版本 3.18.4。

检查时共有 **61 个开放 issue 和 5 个开放 PR**。已读取全部 issue 正文、所有返回的评论，以及 #167、#156、#153 的日志附件。截图附件没有逐张验证；需要真站 DOM、账号环境或平台记录的项目保留待验证。

本次只在 `cncagn/Autovisor` 提交和合并修复；上游 issue 不会随 fork 的 PR 被关闭。

## 本次实现与验证范围

- 融合目录按叶子课时识别，隔离兄弟小节的完成图标/进度，保留独立课时和 DOM 顺序。
- 融合课和旧版课点击限定在课时内部的标题；激活判断覆盖独立小节及内部 item-box，仍保留失败超时。
- 播放回退或重播时刷新活动基准；真正冻结的学习和复习仍在 120 秒后失败。
- Windows 窗口操作在句柄失效时有限重试，持续失败后提示手动操作。
- 失败课程的最终日志正确标记“全部完成=False”。
- 缺少课时标题时不再借用页面其他章节的标题；融合标题保留独立章节编号。

测试使用合成 HTML、Playwright Chromium 和可控时钟，不登录智慧树、不写入真实学习记录。Windows 本地完整 unittest 共 123 项，120 项通过、3 项平台相关跳过；CI 覆盖 Windows/Linux Python 3.10/3.13，及原有 macOS 两种架构的 smoke 流程。CI 最终结果见合并 PR 的检查记录。

## 全部 issue

| Issue | 标题 | 结论 | 依据 / 后续 |
| --- | --- | --- | --- |
| [#167](https://github.com/CXRunfree/Autovisor/issues/167) | 新版共享课无法正常刷课 | 部分修复，待 DOM | 附件确认 legacy 激活超时；增加限定在本课时内的 #lessonOrder 点击，并修正 failed 时“全部完成=True”的日志。真实网页标记不明，不能声称完全解决。 |
| [#166](https://github.com/CXRunfree/Autovisor/issues/166) | [Bug] 融合共享课完成第1节后无法选中第2节课时：课时激活超时（fusion / .chapter-content-second.current） | 机制修复，待真站复核 | 改为叶子小节；点击自身标题；支持小节、独立课时和 item-box 的 current 标记。离线 DOM 复现通过；报告课程的真实 DOM 未提供。 |
| [#165](https://github.com/CXRunfree/Autovisor/issues/165) | 您的脚本被盗用引流至刷课下单平台 | 非代码问题 | 盗用举报、其他项目推广、感谢或杀毒软件讨论；无可复现的本仓库代码缺陷。 |
| [#164](https://github.com/CXRunfree/Autovisor/issues/164) | 学习通刷课 | 非代码问题 | 盗用举报、其他项目推广、感谢或杀毒软件讨论；无可复现的本仓库代码缺陷。 |
| [#163](https://github.com/CXRunfree/Autovisor/issues/163) | [Feature Request] 检测到安全验证时提供可选的桌面弹窗提醒 | 待实现功能 | 可选桌面验证提醒尚未实现；现有代码仅终端提醒和按配置前置浏览器。 |
| [#157](https://github.com/CXRunfree/Autovisor/issues/157) | 共享智慧课依旧无法使用 | 待真实页面 | 新课程/AI 课程结构缺少可用 DOM。#156 附件实际为目录加载超时。现有支持不能证明覆盖报告的每类页面。 |
| [#156](https://github.com/CXRunfree/Autovisor/issues/156) | 共享课视频卡住超时退出 | 待真实页面 | 新课程/AI 课程结构缺少可用 DOM。#156 附件实际为目录加载超时。现有支持不能证明覆盖报告的每类页面。 |
| [#154](https://github.com/CXRunfree/Autovisor/issues/154) | ai-smart-courese无法自动刷课 | 待真实页面 | 新课程/AI 课程结构缺少可用 DOM。#156 附件实际为目录加载超时。现有支持不能证明覆盖报告的每类页面。 |
| [#153](https://github.com/CXRunfree/Autovisor/issues/153) | 未准确识别平台进度导致播放完当前视频后播放下个视频一段时间后脚本误认视频停止使脚本终止 | 机制修复，平台问题待验 | 回退后使用新的播放时间基准，避免等到历史最高播放点才认定活动。仍要求平台确认完成；平台进度恒为零的具体原因尚未证实。 |
| [#152](https://github.com/CXRunfree/Autovisor/issues/152) | [ERROR] 程序运行时出现未处理异常. | 需当前版本日志 | 截图、旧版日志或信息不足；#109 评论称中文路径相关，当前工作目录含中文且测试通过，但尚无对应真实运行复现。 |
| [#146](https://github.com/CXRunfree/Autovisor/issues/146) | 任务点被重置 | 待平台侧验证 | 任务点重置、倍速与平台记录或前后台计时涉及服务端规则；保留平台完成确认，不能仅按播放器时间判定学完。 |
| [#143](https://github.com/CXRunfree/Autovisor/issues/143) | 无法打开链接 | 配置/待复现 | 需课程播放页有效网址及当前配置。#143 评论指向无效 URL2；#99 已有用户反馈配置正确链接后恢复。当前仍需要个案日志。 |
| [#142](https://github.com/CXRunfree/Autovisor/issues/142) | 不会自动跳转到下一集 | 相关机制已覆盖，待个案复核 | 当前多目录适配加本次小节隔离和精确点击覆盖常见跳转原因；历史报告缺少同版本可复现 DOM，不能批量标记解决。 |
| [#139](https://github.com/CXRunfree/Autovisor/issues/139) | 是否支持智慧课程 | 待真实页面 | 新课程/AI 课程结构缺少可用 DOM。#156 附件实际为目录加载超时。现有支持不能证明覆盖报告的每类页面。 |
| [#136](https://github.com/CXRunfree/Autovisor/issues/136) | 几乎重写了整个项目用于刷ai型课程 | 其他实现/功能讨论 | 第三方 fork 或 GUI 方案不直接整体合并；涉及课程种类、并行或界面行为，需要分别验证兼容性。 |
| [#134](https://github.com/CXRunfree/Autovisor/issues/134) | 无法开始刷课 | 需当前版本日志 | 截图、旧版日志或信息不足；#109 评论称中文路径相关，当前工作目录含中文且测试通过，但尚无对应真实运行复现。 |
| [#133](https://github.com/CXRunfree/Autovisor/issues/133) | 新课程类型ai-smart-course兼容 | 其他实现/功能讨论 | 第三方 fork 或 GUI 方案不直接整体合并；涉及课程种类、并行或界面行为，需要分别验证兼容性。 |
| [#129](https://github.com/CXRunfree/Autovisor/issues/129) | 无法自动进入下一章节，单个视频无限循环 | 相关机制已覆盖，待个案复核 | 当前多目录适配加本次小节隔离和精确点击覆盖常见跳转原因；历史报告缺少同版本可复现 DOM，不能批量标记解决。 |
| [#127](https://github.com/CXRunfree/Autovisor/issues/127) | 翻转课失效 | 现有代码覆盖，待真站验证 | 已完成课程会转入复习模式；#127 评论称错误发生在学完翻转课后。已有逻辑和离线融合课复习测试不等同于翻转课真站验证。 |
| [#124](https://github.com/CXRunfree/Autovisor/issues/124) | 倍速调用问题 | 待平台侧验证 | 任务点重置、倍速与平台记录或前后台计时涉及服务端规则；保留平台完成确认，不能仅按播放器时间判定学完。 |
| [#120](https://github.com/CXRunfree/Autovisor/issues/120) | 尝试自己改一版通过元素选择仍然复现线路异常【附加原版log日志】 | 平台验证/待复现 | 线路异常与验证涉及平台响应；需当前版本完整日志与页面，未移植第三方登录或验证实现。 |
| [#116](https://github.com/CXRunfree/Autovisor/issues/116) | 章节无法跳过 | 相关机制已覆盖，待个案复核 | 当前多目录适配加本次小节隔离和精确点击覆盖常见跳转原因；历史报告缺少同版本可复现 DOM，不能批量标记解决。 |
| [#115](https://github.com/CXRunfree/Autovisor/issues/115) | 建议增加跳过非文本的文件 | 待非视频目录样本 | 混合 PPT/PDF/视频目录需可靠资源类型标记；尚未实现通用非视频过滤，不能盲目跳过含视频的章节。 |
| [#114](https://github.com/CXRunfree/Autovisor/issues/114) | 请问，弹了两行代码就自动退出了 | 配置/待复现 | 需课程播放页有效网址及当前配置。#143 评论指向无效 URL2；#99 已有用户反馈配置正确链接后恢复。当前仍需要个案日志。 |
| [#111](https://github.com/CXRunfree/Autovisor/issues/111) | 可以可以 | 非代码问题 | 盗用举报、其他项目推广、感谢或杀毒软件讨论；无可复现的本仓库代码缺陷。 |
| [#110](https://github.com/CXRunfree/Autovisor/issues/110) | 显示错误 | 需当前版本日志 | 截图、旧版日志或信息不足；#109 评论称中文路径相关，当前工作目录含中文且测试通过，但尚无对应真实运行复现。 |
| [#109](https://github.com/CXRunfree/Autovisor/issues/109) | 任务函数video_optimize 出现异常 | 需当前版本日志 | 截图、旧版日志或信息不足；#109 评论称中文路径相关，当前工作目录含中文且测试通过，但尚无对应真实运行复现。 |
| [#108](https://github.com/CXRunfree/Autovisor/issues/108) | 程序异常崩溃 | 需当前版本日志 | 截图、旧版日志或信息不足；#109 评论称中文路径相关，当前工作目录含中文且测试通过，但尚无对应真实运行复现。 |
| [#106](https://github.com/CXRunfree/Autovisor/issues/106) | 小的斗胆写了个图形界面，还请大佬笑纳 | 其他实现/功能讨论 | 第三方 fork 或 GUI 方案不直接整体合并；涉及课程种类、并行或界面行为，需要分别验证兼容性。 |
| [#105](https://github.com/CXRunfree/Autovisor/issues/105) | 被检测到了 | 平台验证/待复现 | 现有代码等待用户完成可见验证；本次没有增加绕过平台检测的功能，未验证个案的异常脚本提示。 |
| [#102](https://github.com/CXRunfree/Autovisor/issues/102) | 重启电脑之后，窗口闪退 | 需当前版本日志 | 截图、旧版日志或信息不足；#109 评论称中文路径相关，当前工作目录含中文且测试通过，但尚无对应真实运行复现。 |
| [#101](https://github.com/CXRunfree/Autovisor/issues/101) | error(1400, 'MoveWindow', '无效的窗口句柄。') | 异常路径已修复 | 失效的 Windows 原生窗口句柄重新获取一次；再次失败只提示手动切换窗口，不终止播放。模拟异常回归通过。 |
| [#99](https://github.com/CXRunfree/Autovisor/issues/99) | 弹出未检出到有效网址 | 配置/待复现 | 需课程播放页有效网址及当前配置。#143 评论指向无效 URL2；#99 已有用户反馈配置正确链接后恢复。当前仍需要个案日志。 |
| [#98](https://github.com/CXRunfree/Autovisor/issues/98) | 刷课倍速问题 | 待平台侧验证 | 任务点重置、倍速与平台记录或前后台计时涉及服务端规则；保留平台完成确认，不能仅按播放器时间判定学完。 |
| [#97](https://github.com/CXRunfree/Autovisor/issues/97) | 能否添加重复刷课功能？ | 现有代码覆盖，待真站验证 | 已完成课程会转入复习模式；#127 评论称错误发生在学完翻转课后。已有逻辑和离线融合课复习测试不等同于翻转课真站验证。 |
| [#96](https://github.com/CXRunfree/Autovisor/issues/96) | 启动不了 | 配置/待复现 | 需课程播放页有效网址及当前配置。#143 评论指向无效 URL2；#99 已有用户反馈配置正确链接后恢复。当前仍需要个案日志。 |
| [#95](https://github.com/CXRunfree/Autovisor/issues/95) | 运行成功了，但是每次运行仅限电脑重启，后台把Edge关了，也无法二次启动程序 | 待浏览器环境复现 | 浏览器二次启动/兼容问题需要进程状态和 Playwright 错误；已有独立浏览器会话逻辑不足以证明根因。 |
| [#94](https://github.com/CXRunfree/Autovisor/issues/94) | 如图，无法使用 | 异常路径已修复 | 失效的 Windows 原生窗口句柄重新获取一次；再次失败只提示手动切换窗口，不终止播放。模拟异常回归通过。 |
| [#93](https://github.com/CXRunfree/Autovisor/issues/93) | 智慧树新形态课程无法正常运行 | 待真实页面 | 新课程/AI 课程结构缺少可用 DOM。#156 附件实际为目录加载超时。现有支持不能证明覆盖报告的每类页面。 |
| [#92](https://github.com/CXRunfree/Autovisor/issues/92) | 智慧树已经正式上线人机检测域名拦截功能的反制措施 | 平台验证/待复现 | 现有代码等待用户完成可见验证；本次没有增加绕过平台检测的功能，未验证个案的异常脚本提示。 |
| [#91](https://github.com/CXRunfree/Autovisor/issues/91) | 提示检测到异常脚本 | 平台验证/待复现 | 现有代码等待用户完成可见验证；本次没有增加绕过平台检测的功能，未验证个案的异常脚本提示。 |
| [#84](https://github.com/CXRunfree/Autovisor/issues/84) | 部分网课无法检测进度 | 已有相关超时修复，待个案验证 | 可选隐藏弹窗等待已有上限；目录和平台进度适配已有实现。历史问题缺少当前版本页面证据。 |
| [#81](https://github.com/CXRunfree/Autovisor/issues/81) | 无法正常打开浏览器，一直刷新，如视频 | 登录/待当前复现 | 当前支持新旧登录域名和手动登录；旧日志存在登录回跳和隐藏弹窗等待，不能仅由历史日志确认目前已解决。 |
| [#80](https://github.com/CXRunfree/Autovisor/issues/80) | 智能课无法自动答题 | 待真实页面 | 新课程/AI 课程结构缺少可用 DOM。#156 附件实际为目录加载超时。现有支持不能证明覆盖报告的每类页面。 |
| [#79](https://github.com/CXRunfree/Autovisor/issues/79) | 无法读取进度，无法自动切换下一集 | 已有相关超时修复，待个案验证 | 可选隐藏弹窗等待已有上限；目录和平台进度适配已有实现。历史问题缺少当前版本页面证据。 |
| [#77](https://github.com/CXRunfree/Autovisor/issues/77) | 浏览器启动失败，只有重启系统后才能继续用 | 待浏览器环境复现 | 浏览器二次启动/兼容问题需要进程状态和 Playwright 错误；已有独立浏览器会话逻辑不足以证明根因。 |
| [#76](https://github.com/CXRunfree/Autovisor/issues/76) | 带有ppt的新页面课程播放完无法跳转下一章 | 待非视频目录样本 | 混合 PPT/PDF/视频目录需可靠资源类型标记；尚未实现通用非视频过滤，不能盲目跳过含视频的章节。 |
| [#75](https://github.com/CXRunfree/Autovisor/issues/75) | 等待页面上的 video 元素出现时超时 | 待非视频目录样本 | 混合 PPT/PDF/视频目录需可靠资源类型标记；尚未实现通用非视频过滤，不能盲目跳过含视频的章节。 |
| [#72](https://github.com/CXRunfree/Autovisor/issues/72) | 我想问问这是怎么回事 | 现有代码覆盖 | 镜像切换及未知总长度下载已有处理和安装器测试；原 ZeroDivisionError 来自旧版下载进度。 |
| [#69](https://github.com/CXRunfree/Autovisor/issues/69) | Edge&&智慧共享课无法播放视频&&附log | 待非视频目录样本 | 混合 PPT/PDF/视频目录需可靠资源类型标记；尚未实现通用非视频过滤，不能盲目跳过含视频的章节。 |
| [#68](https://github.com/CXRunfree/Autovisor/issues/68) | 记得关了病毒查杀 | 非代码问题 | 盗用举报、其他项目推广、感谢或杀毒软件讨论；无可复现的本仓库代码缺陷。 |
| [#66](https://github.com/CXRunfree/Autovisor/issues/66) | 建议增加检测PPT功能 | 待非视频目录样本 | 混合 PPT/PDF/视频目录需可靠资源类型标记；尚未实现通用非视频过滤，不能盲目跳过含视频的章节。 |
| [#65](https://github.com/CXRunfree/Autovisor/issues/65) | [Chrome & Edge] Bug 进入播放页面后无法自动跳转到未播放的视频 | 相关机制已覆盖，待个案复核 | 当前多目录适配加本次小节隔离和精确点击覆盖常见跳转原因；历史报告缺少同版本可复现 DOM，不能批量标记解决。 |
| [#58](https://github.com/CXRunfree/Autovisor/issues/58) | （Google）建议改进：刷课在弹出问题时，将浏览器窗口前置，然后隔0.25秒/0.5秒/1秒窗口自动后置 | 待平台侧验证 | 任务点重置、倍速与平台记录或前后台计时涉及服务端规则；保留平台完成确认，不能仅按播放器时间判定学完。 |
| [#54](https://github.com/CXRunfree/Autovisor/issues/54) | 无法读取前缀为smartcoursestudent.zhihuishu.com的课程链接 | 待真实页面 | 新课程/AI 课程结构缺少可用 DOM。#156 附件实际为目录加载超时。现有支持不能证明覆盖报告的每类页面。 |
| [#53](https://github.com/CXRunfree/Autovisor/issues/53) | 一直卡在“开始加载播放页” | 已有相关超时修复，待个案验证 | 可选隐藏弹窗等待已有上限；目录和平台进度适配已有实现。历史问题缺少当前版本页面证据。 |
| [#50](https://github.com/CXRunfree/Autovisor/issues/50) | 无法自动跳到下一集，一集内死循环，无法跳过已经刷过的视频，完成度和进度条不等 | 相关机制已覆盖，待个案复核 | 当前多目录适配加本次小节隔离和精确点击覆盖常见跳转原因；历史报告缺少同版本可复现 DOM，不能批量标记解决。 |
| [#48](https://github.com/CXRunfree/Autovisor/issues/48) | 问题 | 待真站复现 | 弹题焦点及验证后黑屏需页面状态；保持人工验证等待和平台确认，不按播放器播放状态宣称修复。 |
| [#40](https://github.com/CXRunfree/Autovisor/issues/40) | 自动播放下一集 | 相关机制已覆盖，待个案复核 | 当前多目录适配加本次小节隔离和精确点击覆盖常见跳转原因；历史报告缺少同版本可复现 DOM，不能批量标记解决。 |
| [#36](https://github.com/CXRunfree/Autovisor/issues/36) | 部分课程失效 | 相关机制已覆盖，待个案复核 | 当前多目录适配加本次小节隔离和精确点击覆盖常见跳转原因；历史报告缺少同版本可复现 DOM，不能批量标记解决。 |
| [#34](https://github.com/CXRunfree/Autovisor/issues/34) | 安全验证后新视频黑屏无法正常播放，切换下一门课程后黑屏不能正常播放 | 待真站复现 | 弹题焦点及验证后黑屏需页面状态；保持人工验证等待和平台确认，不按播放器播放状态宣称修复。 |

## 开放 PR 检查

| 上游 PR | 处理 |
| --- | --- |
| [#159](https://github.com/CXRunfree/Autovisor/pull/159) | 参考并移植 Kemou2333 的标题处理与合成浏览器 fixture/test；来源提交 `85eeda36a9feb4a89452b3104f61c02f392b9953`。目录选择进一步改为任意层级叶子课时，避免仅处理直接子节点。保留原 MIT 许可。 |
| [#162](https://github.com/CXRunfree/Autovisor/pull/162) | 审查了小节定位和播放回退方案。本次实现有限失败语义及回退基准修复；没有整体移植其无限等待、手动切课接续重构。 |
| [#161](https://github.com/CXRunfree/Autovisor/pull/161) | 外部 DeepSeek 视觉验证包含额外 API 配置、联网与计费，不属于本次可复现播放缺陷修复，未移植。 |
| [#145](https://github.com/CXRunfree/Autovisor/pull/145) | macOS/自动播放方案与当前已有 macOS 启动、浏览器适配和课程循环重叠；未整体合并旧实现。 |
| [#144](https://github.com/CXRunfree/Autovisor/pull/144) | 自动抗暂停和进程看门狗重启改变失败处理行为，未直接移植；当前保留有界停滞检测。 |
