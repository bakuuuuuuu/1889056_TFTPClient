# 소켓, 구조체, 인수 구문 분석 라이브러리 가져오기
import socket
import argparse
from struct import pack, unpack

# 기본 포트, 블록 크기 및 TFTP 전송 모드 정의
DEFAULT_PORT = 69
BLOCK_SIZE = 512
DEFAULT_TRANSFER_MODE = 'netascii'

# TFTP Opcode 및 Error 코드 정의
OPCODE = {'RRQ': 1, 'WRQ': 2, 'DATA': 3, 'ACK': 4, 'ERROR': 5}
ERROR_CODE = {
    0: "Not defined, see error message (if any).",
    1: "File not found.",
    2: "Access violation.",
    3: "Disk full or allocation exceeded.",
    4: "Illegal TFTP operation.",
    5: "Unknown transfer ID.",
    6: "File already exists.",
    7: "No such user."
}

# 서버에 파일 작성 요청 메시지(WRQ) 전송 함수
def send_wrq(sock, server_address, filename, mode):
    format = f'>h{len(filename)}sB{len(mode)}sB'
    wrq_message = pack(format, OPCODE['WRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(wrq_message, server_address)

# 서버에 파일 읽기 요청 메시지(RRQ) 전송 함수
def send_rrq(sock, server_address, filename, mode):
    format = f'>h{len(filename)}sB{len(mode)}sB'
    rrq_message = pack(format, OPCODE['RRQ'], bytes(filename, 'utf-8'), 0, bytes(mode, 'utf-8'), 0)
    sock.sendto(rrq_message, server_address)

# 서버 ACK 메시지 전송 함수
def send_ack(sock, server_address, seq_num):
    format = f'>hh'
    ack_message = pack(format, OPCODE['ACK'], seq_num)
    sock.sendto(ack_message, server_address)

# 서버에 DATA 메시지 전송 함수
def send_data(sock, server_address, block_num, data):
    format = f'>hh{len(data)}s'
    data_message = pack(format, OPCODE['DATA'], block_num, data)
    sock.sendto(data_message, server_address)

# 명령 줄 인수 구문 분석 및 검증
parser = argparse.ArgumentParser(description='TFTP client program')
parser.add_argument("host", help="Server IP address", type=str)
parser.add_argument("action", help="get or put a file", type=str)
parser.add_argument("filename", help="name of file to transfer", type=str)
parser.add_argument("-p", "--port", help="Server port number", type=int, default=DEFAULT_PORT)
args = parser.parse_args()

# UDP 소켓 생성 및 서버 주소 정의
server_address = (args.host, args.port)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 요청 유형에 따라 WRQ 또는 RRQ 메시지 전송
mode = DEFAULT_TRANSFER_MODE
if args.action == "get":
    send_rrq(sock, server_address, args.filename, mode)
    file = open(args.filename, "wb")
    seq_number = 0
elif args.action == "put":
    send_wrq(sock, server_address, args.filename, mode)
    file = open(args.filename, "rb")
    seq_number = 1

try:
    while True:
        # 서버로부터 데이터 및 Opcode 수신
        data, server = sock.recvfrom(516)
        opcode = int.from_bytes(data[:2], 'big')

        # Opcode에 따른 작업 처리
        if opcode == OPCODE['DATA']:
            seq_number = int.from_bytes(data[2:4], 'big')
            send_ack(sock, server, seq_number)  # ACK 전송
            file_block = data[4:]
            file.write(file_block)

            if len(file_block) < BLOCK_SIZE:
                break
        elif opcode == OPCODE['ACK']:
            seq_number = int.from_bytes(data[2:4], 'big')
            file_block = file.read(BLOCK_SIZE)

            if len(file_block) == 0:
                break

            send_data(sock, server, seq_number + 1, file_block) # DATA 전송
            if len(file_block) < BLOCK_SIZE:
                break
        elif opcode == OPCODE['ERROR']:
            error_code = int.from_bytes(data[2:4], byteorder='big')
            print(ERROR_CODE[error_code])  # 에러 출력
            break
        else:
            break
finally:
    file.close() # 파일 닫기
    sock.close() # 소켓 닫기