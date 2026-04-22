#!/usr/bin/env python3
"""
猜数字游戏 (Guess Number Game)
一个在终端运行的简单猜数字游戏。
程序随机生成1-100的数字，用户输入猜测，程序提示大了还是小了，直到猜对为止。
"""

import random
import sys


def display_welcome():
    """显示欢迎信息和游戏规则"""
    print("=" * 50)
    print("欢迎来到猜数字游戏！")
    print("=" * 50)
    print("游戏规则：")
    print("1. 程序会随机生成一个1到100之间的整数")
    print("2. 你需要猜测这个数字是多少")
    print("3. 每次猜测后，程序会告诉你猜大了还是猜小了")
    print("4. 直到你猜对为止")
    print("=" * 50)
    print()


def get_user_guess():
    """获取用户输入并验证"""
    while True:
        try:
            guess = input("请输入你的猜测 (1-100)，或输入 'q' 退出游戏: ").strip()
            
            # 检查是否要退出
            if guess.lower() == 'q':
                return None
            
            guess_num = int(guess)
            
            if 1 <= guess_num <= 100:
                return guess_num
            else:
                print("请输入1到100之间的数字！")
                
        except ValueError:
            print("请输入有效的数字！")
        except KeyboardInterrupt:
            print("\n游戏被中断。")
            return None


def play_game():
    """游戏主逻辑"""
    # 生成随机数字
    target_number = random.randint(1, 100)
    attempts = 0
    
    print(f"我已经想好了一个1到100之间的数字，开始猜吧！")
    print()
    
    while True:
        # 获取用户猜测
        guess = get_user_guess()
        
        # 用户选择退出
        if guess is None:
            print(f"游戏结束。正确答案是: {target_number}")
            return False
        
        attempts += 1
        
        # 判断猜测结果
        if guess < target_number:
            print(f"第{attempts}次尝试: {guess} -> 猜小了！")
        elif guess > target_number:
            print(f"第{attempts}次尝试: {guess} -> 猜大了！")
        else:
            print(f"恭喜你！第{attempts}次尝试: {guess} -> 猜对了！")
            print(f"你用了 {attempts} 次猜中了数字 {target_number}！")
            return True
        
        print()


def ask_play_again():
    """询问是否再玩一次"""
    while True:
        answer = input("是否再玩一次？(y/n): ").strip().lower()
        if answer in ['y', 'yes', '是']:
            return True
        elif answer in ['n', 'no', '否']:
            return False
        else:
            print("请输入 y/n 或 是/否")


def main():
    """程序主函数"""
    display_welcome()
    
    play_count = 0
    total_attempts = 0
    
    while True:
        play_count += 1
        print(f"\n第 {play_count} 轮游戏")
        print("-" * 30)
        
        # 玩一轮游戏
        success = play_game()
        
        if success:
            # 这里可以记录游戏统计信息
            # 在实际游戏中，attempts 是在 play_game 函数中统计的
            # 为了简化，我们这里只显示轮数
            pass
        
        # 询问是否继续
        if not ask_play_again():
            break
    
    # 游戏结束统计
    print("\n" + "=" * 50)
    print("游戏统计：")
    print(f"总游戏轮数: {play_count}")
    print("感谢游玩！再见！")
    print("=" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n游戏被中断。再见！")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序出现错误: {e}")
        sys.exit(1)