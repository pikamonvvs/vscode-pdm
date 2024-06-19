import keyboard


def on_key_event(event):
    print(f"키 '{event.name}'가 눌렸습니다.")


def on_enter_key(event):
    print("엔터 키가 눌렸습니다. 특정 동작을 수행합니다.")


def main():
    print("키보드 입력을 감지합니다. 종료하려면 'esc' 키를 누르세요.")

    # 특정 키가 눌렸을 때 콜백 함수를 호출합니다.
    keyboard.on_press(on_key_event)
    keyboard.on_press_key("enter", on_enter_key)

    # 'esc' 키가 눌리면 프로그램을 종료합니다.
    keyboard.wait("esc")

    print("프로그램이 종료되었습니다.")


if __name__ == "__main__":
    main()
