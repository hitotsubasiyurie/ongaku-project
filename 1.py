import sys
import subprocess

def func_x():
    print("func_x 终端已启动")
    while True:
        s = input("func_x 输入: ")
        print("func_x 收到:", s)

def main():
    print("main 运行中")

    # 在新终端启动当前脚本，并指定执行 func_x
    subprocess.Popen(
        [sys.executable, __file__, "--funcx"],
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    # main 继续运行
    while True:
        s = input("main 输入: ")
        print("main 收到:", s)

if __name__ == "__main__":
    if "--funcx" in sys.argv:
        func_x()
    else:
        main()
