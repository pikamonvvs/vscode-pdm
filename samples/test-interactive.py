import sys
import threading
import time

from loguru import logger

# 로그 파일 설정
logger.remove()
logger.add("logfile.log", rotation="1 MB")

# 콘솔 로그 핸들러 ID 저장
console_handler_id = logger.add(sys.stdout, level="INFO")

# 로그 출력 플래그
log_active = True


def log_message():
    while True:
        if log_active:
            logger.info("This is a log message.")
        time.sleep(1)


def user_input():
    global log_active
    global console_handler_id
    while True:
        user_input = input("Enter 'd' to disable console log, 'x' to enable console log: ")
        if user_input == "d":
            logger.remove(console_handler_id)
            log_active = False
        elif user_input == "x":
            console_handler_id = logger.add(sys.stdout, level="INFO")
            log_active = True


# 로그 메시지를 출력하는 스레드 시작
log_thread = threading.Thread(target=log_message)
log_thread.daemon = True
log_thread.start()

# 사용자 입력을 받는 스레드 시작
input_thread = threading.Thread(target=user_input)
input_thread.daemon = True
input_thread.start()

# 메인 스레드가 종료되지 않도록 유지
while True:
    time.sleep(1)
