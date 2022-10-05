import e2_pb2
import sys

def main():
    print("hello")
    smes = e2_pb2.SimpleMessage()
    smes.lucky_number = 11
    buf = smes.SerializeToString()
    print(buf)
    print(smes)

    e2res = e2_pb2.E2_dummy_response()
    e2res.req_id = 100
    e2res.mess_string = "ciaooo"
    e2res.result = True

    buf = e2res.SerializeToString()
    print(buf)
    print(e2res)

if __name__ == "__main__":
    main()
