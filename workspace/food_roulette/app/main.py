import sys
import time
import random
import os

class FoodRoulette:
    def __init__(self):
        # 预设菜单
        self.menu = [
            "火锅", "烧烤", "麦当劳", "肯德基",
            "炒饭", "麻辣烫", "沙拉", "饿着", "袁记云饺"
        ]
        self.speed_factors = [0.05, 0.08, 0.12, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.7, 1.0]
        
    def clear_screen(self):
        """清屏函数，兼容不同操作系统"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """打印标题"""
        print("=" * 50)
        print("           今天吃什么大转盘")
        print("=" * 50)
        print(f"候选菜单: {', '.join(self.menu)}")
        print("-" * 50)
    
    def spin_roulette(self):
        """执行转盘抽奖动画"""
        print("\n转盘开始转动... 按 Ctrl+C 可中断")
        print("准备...")
        time.sleep(1)
        
        # 随机决定最终结果
        final_index = random.randint(0, len(self.menu) - 1)
        final_food = self.menu[final_index]
        
        # 转盘动画
        current_index = 0
        cycles = 3  # 转3圈
        
        for speed_factor in self.speed_factors:
            for _ in range(len(self.menu) * cycles // len(self.speed_factors)):
                self.clear_screen()
                self.print_header()
                
                # 打印当前转盘状态
                print("\n当前指向: ", end="")
                for i, food in enumerate(self.menu):
                    if i == current_index:
                        print(f"[ {food} ]", end=" ")
                    else:
                        print(f"  {food}  ", end=" ")
                print("\n")
                
                # 移动指针
                current_index = (current_index + 1) % len(self.menu)
                time.sleep(speed_factor)
            
            cycles = max(1, cycles - 1)  # 逐渐减少圈数
        
        # 最终定格
        for _ in range(5):  # 闪烁效果
            self.clear_screen()
            self.print_header()
            
            if _ % 2 == 0:
                print("\n" + "*" * 50)
                print(f"         恭喜！今天吃: {final_food} !")
                print("*" * 50)
            else:
                print("\n" + "-" * 50)
                print(f"         恭喜！今天吃: {final_food} !")
                print("-" * 50)
            
            time.sleep(0.3)
        
        # 最终显示
        self.clear_screen()
        self.print_header()
        print("\n" + "=" * 50)
        print(f"         ⭐ 最终结果: {final_food} ⭐")
        print("=" * 50)
        
        return final_food
    
    def ask_retry(self):
        """询问是否重新抽奖"""
        while True:
            try:
                choice = input("\n输入回车重新抽奖，输入 'q' 退出: ").strip().lower()
                
                if choice == 'q':
                    return False
                elif choice == '':
                    return True
                else:
                    print("输入无效！请输入回车或 'q'")
            except KeyboardInterrupt:
                print("\n\n检测到中断，程序退出")
                return False
            except Exception as e:
                print(f"发生错误: {e}")
                return False
    
    def run(self):
        """主运行循环"""
        try:
            while True:
                self.clear_screen()
                self.print_header()
                
                # 等待用户按回车开始
                try:
                    input("\n按回车键开始抽奖 (或输入 'q' 退出): ").strip().lower()
                except KeyboardInterrupt:
                    print("\n\n检测到中断，程序退出")
                    break
                
                # 执行抽奖
                try:
                    result = self.spin_roulette()
                    print(f"\n🎉 今天就去吃: {result} ! 🎉")
                except KeyboardInterrupt:
                    print("\n\n抽奖被中断")
                    continue
                except Exception as e:
                    print(f"\n抽奖过程中发生错误: {e}")
                    continue
                
                # 询问是否继续
                if not self.ask_retry():
                    break
                
        except KeyboardInterrupt:
            print("\n\n程序被中断，再见！")
        except Exception as e:
            print(f"\n程序运行出错: {e}")
        finally:
            print("\n感谢使用今天吃什么大转盘！再见！")

def main():
    """程序入口"""
    roulette = FoodRoulette()
    roulette.run()

if __name__ == "__main__":
    main()