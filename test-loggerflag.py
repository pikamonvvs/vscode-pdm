from loguru import logger


# 사용자 정의 필터 함수
def filter_by_flag(record):
    # 'flag'가 'SHOW'인 로그만 출력
    return record["extra"].get("flag") == "SHOW"


# 로그 포맷을 정의하고, 필터를 추가합니다.
logger.add("logfile.log", format="{time} {level} {message} {extra[flag]}", filter=filter_by_flag)


def main():
    # 플래그를 포함한 로그 메시지를 기록합니다.
    logger.info("이것은 보여야 하는 정보 메시지입니다.", extra={"flag": "SHOW"})
    logger.info("이것은 숨겨야 하는 정보 메시지입니다.", extra={"flag": "HIDE"})
    logger.warning("이것은 보여야 하는 경고 메시지입니다.", extra={"flag": "SHOW"})
    logger.error("이것은 숨겨야 하는 에러 메시지입니다.", extra={"flag": "HIDE"})


if __name__ == "__main__":
    main()
