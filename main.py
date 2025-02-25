import requests
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import schedule
import logging
from rich.console import Console
from rich.logging import RichHandler
import os


def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error("❌ 配置文件 config.json 不存在")
        raise
    except json.JSONDecodeError:
        logging.error("❌ 配置文件格式错误")
        raise

CONFIG = load_config()


logging.basicConfig(
    level=getattr(logging, CONFIG['logging']['level']),
    format="%(message)s",
    handlers=[
        logging.FileHandler(CONFIG['logging']['file'], encoding='utf-8'),
        RichHandler(rich_tracebacks=True)
    ]
)

console = Console()

class NewtonBot:
    def __init__(self, session_token, proxy=None):
        self.session_token = session_token
        self.proxy = proxy
        self.wallet_address = None
        self.total_credits = 0
        self.headers = {
            'authority': 'www.magicnewton.com',
            'accept': '*/*',
            'content-type': 'application/json',
            'origin': 'https://www.magicnewton.com',
            'referer': 'https://www.magicnewton.com/portal/rewards',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'cookie': f'__Secure-next-auth.session-token={session_token}'
        }
        
        
        self.tasks = {
            "twitter": {
                "name": "关注推特",
                "questId": "c1ff498a-fae6-4538-b8ae-e73e3ecdc482",
                "metadata": {}
            },
            "discord": {
                "name": "加入DC",
                "questId": "0d46ac52-1d33-437c-a650-d8c79328f6c8",
                "metadata": {}
            },
            "tiktok": {
                "name": "关注TikTok",
                "questId": "c92d51df-459e-4706-bff8-0b027f401733",
                "metadata": {}
            },
            "instagram": {
                "name": "关注Instagram",
                "questId": "d70d0097-6cfb-44d8-9f1c-536bd60dd2b3",
                "metadata": {}
            }
        }
    
    def _make_request(self, method, url, **kwargs):
        if CONFIG['proxy']['enabled'] and self.proxy:
            kwargs['proxies'] = {'http': self.proxy, 'https': self.proxy}
        return requests.request(method, url, **kwargs)
        
    def get_wallet_address(self):
        try:
            response = self._make_request(
                'GET',
                'https://www.magicnewton.com/portal/api/auth/session',
                headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                self.wallet_address = data.get('user', {}).get('name')
                return self.wallet_address
            return None
        except Exception as e:
            logging.error(f"获取钱包地址失败: {str(e)}")
            return None

    def get_total_credits(self):
        try:
            response = self._make_request(
                'GET',
                'https://www.magicnewton.com/portal/api/userQuests',
                headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                total = sum(quest.get('credits', 0) for quest in data.get('data', []))
                return total
            return 0
        except Exception as e:
            logging.error(f"获取总积分失败: {str(e)}")
            return 0

    def press(self):
        payload = {
            "questId": "f56c760b-2186-40cb-9cbc-3af4a3dc20e2",
            "metadata": {"action": "ROLL"}
        }
        
        try:
            response = self._make_request(
                'POST',
                'https://www.magicnewton.com/portal/api/userQuests',
                headers=self.headers,
                json=payload
            )
            if response.status_code == 200:
                data = response.json()
                dice_rolls = data.get('data', {}).get('_diceRolls', [])
                credits = data.get('data', {}).get('credits', 0)
                return True, {'dice_rolls': dice_rolls, 'credits': credits}
            return False, None
        except Exception as e:
            logging.error(f"🎲 Roll请求出错: {str(e)}")
            return False, None

    def bank(self):
        payload = {
            "questId": "f56c760b-2186-40cb-9cbc-3af4a3dc20e2",
            "metadata": {"action": "BANK"}
        }
        
        try:
            response = self._make_request(
                'POST',
                'https://www.magicnewton.com/portal/api/userQuests',
                headers=self.headers,
                json=payload
            )
            return response.status_code == 200
        except Exception as e:
            logging.error(f"💰 Bank请求出错: {str(e)}")
            return False

    def complete_task(self, task_key):
        task = self.tasks.get(task_key)
        if not task:
            return False, "任务不存在"
            
        payload = {
            "questId": task["questId"],
            "metadata": task["metadata"]
        }
        
        try:
            response = self._make_request(
                'POST',
                'https://www.magicnewton.com/portal/api/userQuests',
                headers=self.headers,
                json=payload
            )
            if response.status_code == 200:
                data = response.json()
                return True, data
            return False, "请求失败"
        except Exception as e:
            return False, str(e)

def run_account(session_token, proxy=None):
    bot = NewtonBot(session_token, proxy)
    wallet_address = bot.get_wallet_address() or session_token[:10] + "..."
    
    logging.info(f"🎮 账户：{wallet_address} 开始执行任务")
    
    for i in range(5):
        logging.info(f"🎲 账户：{wallet_address} 进行第{i+1}次roll")
        success, response = bot.press()
        
        if not success:
            logging.error(f"❌ 账户：{wallet_address} 第{i+1}次roll失败，提前结束")
            bot.bank()  
            break
            
        dice_rolls = response['dice_rolls']
        credits = response['credits']
        
        roll_result = '，'.join(map(str, dice_rolls))
        logging.info(f"🎯 账户：{wallet_address} 第{i+1}次骰子点数：{roll_result}，获得积分：{credits}")
        
        if i < 4:
            wait_time = random.uniform(
                CONFIG['execution']['roll_interval']['min_seconds'],
                CONFIG['execution']['roll_interval']['max_seconds']
            )
            time.sleep(wait_time)
    
    
    bot.bank()
    
    total_credits = bot.get_total_credits()
    next_time = datetime.now() + timedelta(hours=CONFIG['execution']['interval_hours'])
    
    
    logging.info(f"✨ 账户：{wallet_address} 任务完成！总积分：{total_credits}")
    logging.info(f"⏰ 账户：{wallet_address} 下次执行时间：{next_time.strftime('%Y-%m-%d %H:%M:%S')}")

def execute_tasks():
    logging.info("🚀 开始执行定时任务...")
    
    try:
        
        with open(CONFIG['accounts']['accounts_file'], 'r') as f:
            accounts = [line.strip() for line in f if line.strip()]
        
        
        proxies = None
        if CONFIG['proxy']['enabled']:
            with open(CONFIG['proxy']['proxy_file'], 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
            
            if len(proxies) < len(accounts):
                logging.error("❌ 代理数量少于账户数量")
                return
        
        
        if CONFIG['concurrent']['enabled']:
            with ThreadPoolExecutor(max_workers=CONFIG['concurrent']['max_workers']) as executor:
                if proxies:
                    for session_token, proxy in zip(accounts, proxies):
                        executor.submit(run_account, session_token, proxy)
                else:
                    for session_token in accounts:
                        executor.submit(run_account, session_token)
        else:
            for i, session_token in enumerate(accounts):
                proxy = proxies[i] if proxies else None
                run_account(session_token, proxy)
                
    except Exception as e:
        logging.error(f"❌ 执行任务时发生错误: {str(e)}")

def print_banner():
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                     🎲 MagicNewton Bot 🎲                    ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  🐦 Twitter: https://x.com/SniffTunes                        ║
    ║  👨‍💻 Author: SniffTunes                                      ║
    ║  🌟 Version: 1.0.0                                           ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold blue")

def execute_tasks_interaction(session_token, proxy=None):
    bot = NewtonBot(session_token, proxy)
    wallet_address = bot.get_wallet_address() or session_token[:10] + "..."
    
    logging.info(f"🎮 账户：{wallet_address} 开始执行社交任务")
    
    for task_key, task_info in bot.tasks.items():
        logging.info(f"📝 账户：{wallet_address} 正在完成{task_info['name']}")
        success, response = bot.complete_task(task_key)
        
        if success:
            credits = response.get('data', {}).get('credits', 0)
            logging.info(f"✅ 账户：{wallet_address} 完成{task_info['name']}，获得积分：{credits}")
        else:
            logging.error(f"❌ 账户：{wallet_address} 完成{task_info['name']}失败：{response}")
            
        
        time.sleep(random.uniform(1, 3))
    
    total_credits = bot.get_total_credits()
    logging.info(f"✨ 账户：{wallet_address} 所有社交任务完成！总积分：{total_credits}")

def show_menu():
    menu = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                     🎲 MagicNewton Bot 🎲                   ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  1. 📝 完成任务交互                                          ║
    ║  2. 🎲 日常扔骰子                                            ║
    ║  3. 🚪 退出程序                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    console.print(menu, style="bold blue")
    return input("请选择功能 (1-3): ")

def main():
    print_banner()
    
    while True:
        choice = show_menu()
        
        if choice == "1":
            logging.info("🚀 开始执行社交任务...")
            try:
                with open(CONFIG['accounts']['accounts_file'], 'r') as f:
                    accounts = [line.strip() for line in f if line.strip()]
                
                proxies = None
                if CONFIG['proxy']['enabled']:
                    with open(CONFIG['proxy']['proxy_file'], 'r') as f:
                        proxies = [line.strip() for line in f if line.strip()]
                
                if CONFIG['concurrent']['enabled']:
                    with ThreadPoolExecutor(max_workers=CONFIG['concurrent']['max_workers']) as executor:
                        if proxies:
                            for session_token, proxy in zip(accounts, proxies):
                                executor.submit(execute_tasks_interaction, session_token, proxy)
                        else:
                            for session_token in accounts:
                                executor.submit(execute_tasks_interaction, session_token)
                else:
                    for i, session_token in enumerate(accounts):
                        proxy = proxies[i] if proxies else None
                        execute_tasks_interaction(session_token, proxy)
                        
            except Exception as e:
                logging.error(f"❌ 执行社交任务时发生错误: {str(e)}")
                
        elif choice == "2":
            
            schedule.every(CONFIG['execution']['interval_hours']).hours.do(execute_tasks)
            execute_tasks()
            while True:
                schedule.run_pending()
                time.sleep(60)
                
        elif choice == "3":
            console.print("👋 感谢使用，再见！", style="bold green")
            break
            
        else:
            console.print("❌ 无效的选择，请重新输入", style="bold red")

if __name__ == "__main__":
    main()
