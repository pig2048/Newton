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

def main():
    print_banner()
    
    schedule.every(CONFIG['execution']['interval_hours']).hours.do(execute_tasks)
    
    
    execute_tasks()
    
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
