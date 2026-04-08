#!/usr/bin/env powershell

<#
.SYNOPSIS
    验证模块的功能和集成

.DESCRIPTION
    验证指定模块的功能，包括环境检查、依赖检查、模块测试、冒烟测试和集成检查

.PARAMETER Module
    要验证的模块名称，可选值：energy_model, path_planner, scheduler, strategies, visualizer, simulation_framework, all

.EXAMPLE
    .\scripts\verify_module.ps1 -Module energy_model
    验证 energy_model 模块

.EXAMPLE
    .\scripts\verify_module.ps1 -Module all
    验证所有模块
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('energy_model', 'path_planner', 'scheduler', 'strategies', 'visualizer', 'simulation_framework', 'all')]
    [string]$Module
)

# 运行 Python 验证脚本
python scripts\verify_module.py $Module