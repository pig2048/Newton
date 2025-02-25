# 🎲 MagicNewton Bot

一个用于自动化执行 MagicNewton 任务的 Python 机器人。

## ✨ 特性

- 🤖 支持多账户并发执行
- 🔄 自动每12小时执行一次
- 🌐 支持代理配置

## 🚀 安装

1. 克隆仓库：

```
git clone https://github.com/pig2048/Newton.git
```

```
cd Newton/
```

2. 安装依赖：

(推荐步骤：)WIN
```
python -m venv venv
```
Linux:
```
source ./venv/bin/activate
```

```
pip install -r requirements.txt
```
## ⚙️ 配置

说明：

accounts.txt 文件中存放的是你的账户信息，每行一个账户。

proxy.txt 文件中存放的是你的代理信息，每行一个代理。
格式：http://X.X.X.X:X

config.json 文件中存放的是你的配置信息,配置是否开启代理并发处理。

## ✔️ 使用
```
python main.py
```

### 详细token获取前往推特进行查看

## 更新
增添了菜单并且供完成简单的任务交互
