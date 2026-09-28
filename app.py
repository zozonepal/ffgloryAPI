from flask import Flask, request, jsonify
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
import requests
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

#━━━━━━━━━━━━━━━━━━━
# Protobuf setup
#━━━━━━━━━━━━━━━━━━━
_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\ndata.proto\"\xbb\x01\n\x04\x44\x61ta\x12\x0f\n\x07\x66ield_2\x18\x02 \x01(\x05\x12\x1e\n\x07\x66ield_5\x18\x05 \x01(\x0b\x32\r.EmptyMessage\x12\x1e\n\x07\x66ield_6\x18\x06 \x01(\x0b\x32\r.EmptyMessage\x12\x0f\n\x07\x66ield_8\x18\x08 \x01(\t\x12\x0f\n\x07\x66ield_9\x18\t \x01(\x05\x12\x1f\n\x08\x66ield_11\x18\x0b \x01(\x0b\x32\r.EmptyMessage\x12\x1f\n\x08\x66ield_12\x18\x0c \x01(\x0b\x32\r.EmptyMessage\"\x0e\n\x0c\x45mptyMessageb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'data1_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    _globals['_DATA']._serialized_start = 15
    _globals['_DATA']._serialized_end = 202
    _globals['_EMPTYMESSAGE']._serialized_start = 204
    _globals['_EMPTYMESSAGE']._serialized_end = 218

Data = _sym_db.GetSymbol('Data')
EmptyMessage = _sym_db.GetSymbol('EmptyMessage')

key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

freefire_version = "OB55"


# ✅ NEW region mapping
def get_region_url(server_name):
    if server_name == "IND":
        url = "https://client.ind.freefiremobile.com"
    elif server_name in {"BR", "US", "SAC", "NA"}:
        url = "https://client.us.freefiremobile.com"
    else:
        url = "https://clientbp.ggpolarbear.com"
    return url


def get_host(base_url):
    if "ind" in base_url:
        return "client.ind.freefiremobile.com"
    elif "us" in base_url:
        return "client.us.freefiremobile.com"
    elif "polarbear" in base_url:
        return "clientbp.ggpolarbear.com"
    return "clientbp.ggpolarbear.com"


def update_bio_with_jwt(jwt_token, bio_text, region="IND"):
    base_url = get_region_url(region)
    url_bio = f"{base_url}/UpdateSocialBasicInfo"

    data = Data()
    data.field_2 = 17
    data.field_5.CopyFrom(EmptyMessage())
    data.field_6.CopyFrom(EmptyMessage())
    data.field_8 = bio_text.replace('+', ' ')
    data.field_9 = 1
    data.field_11.CopyFrom(EmptyMessage())
    data.field_12.CopyFrom(EmptyMessage())

    data_bytes = data.SerializeToString()
    padded_data = pad(data_bytes, AES.block_size)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_data = cipher.encrypt(padded_data)

    headers = {
        "Expect": "100-continue",
        "Authorization": f"Bearer {jwt_token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": freefire_version,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)",
        "Host": get_host(base_url),
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }

    # Fire and forget — response se matlab nahi
    requests.post(url_bio, headers=headers, data=encrypted_data, timeout=10)
    return True


def process_one(acc):
    try:
        jwt_token = acc.get("jwt")
        bio_text = acc.get("bio")
        region = acc.get("region", "IND")

        if not jwt_token or not bio_text:
            return False

        update_bio_with_jwt(jwt_token, bio_text, region)
        return True

    except Exception:
        return False


@app.route('/bio', methods=['POST'])
def update_bio():
    body = request.get_json(silent=True)

    if not body:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    if "accounts" in body and isinstance(body["accounts"], list):
        accounts = body["accounts"]
    elif "jwt" in body:
        accounts = [{
            "jwt": body.get("jwt"),
            "bio": body.get("bio"),
            "region": body.get("region", "IND")
        }]
    else:
        return jsonify({"status": "error", "message": "Provide jwt or accounts"}), 400

    if not accounts:
        return jsonify({"status": "error", "message": "No accounts"}), 400

    # Parallel fire — 20 threads
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(process_one, accounts))

    success_count = sum(1 for r in results if r)
    fail_count = len(results) - success_count

    return jsonify({
        "status": "done",
        "total": len(accounts),
        "success": success_count,
        "failed": fail_count
    }), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)