# 代码提交请求

## 执行命令
请执行以下命令进行本地验证：

```powershell
# 验证修改的模块（替换为实际修改的模块名）
.\scripts\verify_module.ps1 -Module <module_name>

# 提交前总验收
.\scripts\verify_module.ps1 -Module all
```

## 本地验证输出
请粘贴本地验证的完整输出：

```
# 这里粘贴验证输出
```

## 产物路径
请提供生成的产物路径：

- metrics.json: `results/<experiment_name>/<timestamp>/metrics.json`
- records.csv: `results/<experiment_name>/<timestamp>/records.csv`
- chart.png: `results/<experiment_name>/<timestamp>/chart.png`

## 变更说明
请简要描述本次变更的内容和影响：

- 
- 
- 

## 测试结果
请确认以下测试是否通过：

- [ ] 模块单测
- [ ] 冒烟测试
- [ ] 集成检查

## 风险评估
请评估本次变更可能带来的风险：

- 
- 
- 