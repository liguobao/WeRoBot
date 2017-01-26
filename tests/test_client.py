# -*- coding: utf-8 -*-
import os
import responses
import json

from werobot import WeRoBot
from werobot.config import Config
from werobot.client import Client, check_error, ClientException

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

basedir = os.path.dirname(os.path.abspath(__file__))

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
json_header = {'content-type': 'application/json'}
menu_data = {
    "button": [
        {
            "type": "click",
            "name": u"今日歌曲",
            "key": "V1001_TODAY_MUSIC"
        },
        {
            "type": "click",
            "name": u"歌手简介",
            "key": "V1001_TODAY_SINGER"
        },
        {
            "name": u"菜单",
            "sub_button": [
                {
                    "type": "view",
                    "name": u"搜索",
                    "url": "http://www.soso.com/"
                },
                {
                    "type": "view",
                    "name": u"视频",
                    "url": "http://v.qq.com/"
                },
                {
                    "type": "click",
                    "name": u"赞一下我们",
                    "key": "V1001_GOOD"
                }
            ]
        }
    ]}


# callbacks
def token_callback(request):
    return 200, json_header, json.dumps({"access_token": "ACCESS_TOKEN", "expires_in": 7200})


def check_menu_data(item):
    keys = item.keys()
    assert "name" in keys
    if "sub_button" in keys:
        for button in item["sub_button"]:
            check_menu_data(button)
        return
    assert "type" in keys
    if "type" == "click":
        assert "key" in keys
    elif "type" == "view":
        assert "url" in keys
    elif "type" == "media_id" or "type" == "view_limited":
        assert "media_id" in keys


# test case
def test_id_and_secret():
    config = Config()
    config.from_pyfile(os.path.join(basedir, "client_config.py"))
    client = Client(config)
    assert client.appid == "123"
    assert client.appsecret == "321"


def test_robot_client():
    robot = WeRoBot()
    assert robot.client.config == robot.config


def test_check_error():
    error_json = dict(
        error_code=0
    )
    assert error_json == check_error(error_json)

    error_json["error_code"] = 1
    error_json["error_message"] = "test"
    try:
        check_error(error_json)
    except ClientException as e:
        assert str(e) == "1: test"


@responses.activate
def test_grant_token():
    responses.add_callback(responses.GET, TOKEN_URL, callback=token_callback)
    config = Config()
    config.from_pyfile(os.path.join(basedir, "client_config.py"))
    client = Client(config)

    client.grant_token()
    assert client.token == "ACCESS_TOKEN"


@responses.activate
def test_client_request():
    EMPTY_PARAMS_URL = "http://empty-params.werobot.com/"
    DATA_EXISTS_URL = "http://data-exists.werobot.com/"

    def empty_params_callback(request):
        params = urlparse.parse_qs(urlparse.urlparse(request.url).query)
        assert params["access_token"][0] == client.token
        return 200, json_header, json.dumps({"test": "test"})

    def data_exists_url(request):
        assert json.loads(request.body.decode('utf-8')) == {"test": "test"}
        return 200, json_header, json.dumps({"test": "test"})

    responses.add_callback(responses.POST, DATA_EXISTS_URL, callback=data_exists_url)
    responses.add_callback(responses.GET, EMPTY_PARAMS_URL, callback=empty_params_callback)
    responses.add_callback(responses.GET, TOKEN_URL, callback=token_callback)

    config = Config()
    config.from_pyfile(os.path.join(basedir, "client_config.py"))
    client = Client(config)

    r = client.get(url=EMPTY_PARAMS_URL)
    assert r == {"test": "test"}

    r = client.post(url=DATA_EXISTS_URL, data={"test": "test"})
    assert r == {"test": "test"}


@responses.activate
def test_client_create_menu():
    CREATE_URL = "https://api.weixin.qq.com/cgi-bin/menu/create"
    responses.add_callback(responses.GET, TOKEN_URL, callback=token_callback)
    config = Config()
    config.from_pyfile(os.path.join(basedir, "client_config.py"))
    client = Client(config)

    def create_menu_callback(request):
        try:
            body = json.loads(request.body.decode("utf-8"))["button"]
        except KeyError:
            return 200, json_header, json.dumps({"errcode": 1, "errmsg": "error"})
        try:
            for item in body:
                check_menu_data(item)
        except AssertionError:
            return 200, json_header, json.dumps({"errcode": 1, "errmsg": "error"})
        return 200, json_header, json.dumps({"errcode": 0, "errmsg": "ok"})

    responses.add_callback(responses.POST, CREATE_URL, callback=create_menu_callback)

    r = client.create_menu(menu_data)
    assert r == {"errcode": 0, "errmsg": "ok"}

    try:
        client.create_menu({"error": "error"})
    except ClientException as e:
        assert str(e) == "1: error"


@responses.activate
def test_client_group():
    CREATE_URL = "https://api.weixin.qq.com/cgi-bin/groups/create"
    GET_URL = "https://api.weixin.qq.com/cgi-bin/groups/get"
    GET_WITH_ID_URL = "https://api.weixin.qq.com/cgi-bin/groups/getid"
    UPDATE_URL = "https://api.weixin.qq.com/cgi-bin/groups/update"
    MOVE_URL = "https://api.weixin.qq.com/cgi-bin/groups/members/update"
    MOVE_USERS_URL = "https://api.weixin.qq.com/cgi-bin/groups/members/batchupdate"
    DELETE_URL = "https://api.weixin.qq.com/cgi-bin/groups/delete"
    responses.add_callback(responses.GET, TOKEN_URL, callback=token_callback)
    config = Config()
    config.from_pyfile(os.path.join(basedir, "client_config.py"))
    client = Client(config)

    def create_group_callback(request):
        body = json.loads(request.body.decode("utf-8"))
        assert "group" in body.keys()
        assert "name" in body["group"].keys()
        return 200, json_header, json.dumps({"errcode": 0, "errmsg": "ok"})

    responses.add_callback(responses.POST, CREATE_URL, callback=create_group_callback)

    r = client.create_group("test")
    assert r == {"errcode": 0, "errmsg": "ok"}

    def get_group_callback(request):
        return 200, json_header, json.dumps({"errcode": 0, "errmsg": "ok"})

    responses.add_callback(responses.GET, GET_URL, callback=get_group_callback)

    r = client.get_groups()
    assert r == {"errcode": 0, "errmsg": "ok"}

    def get_groups_with_id_callback(request):
        body = json.loads(request.body.decode("utf-8"))
        assert "openid" in body.keys()
        return 200, json_header, json.dumps({"errcode": 0, "errmsg": "ok"})

    responses.add_callback(responses.POST, GET_WITH_ID_URL, callback=get_groups_with_id_callback)

    r = client.get_group_by_id("test")
    assert r == {"errcode": 0, "errmsg": "ok"}

    def update_group_callback(request):
        body = json.loads(request.body.decode("utf-8"))
        assert "group" in body.keys()
        assert "id" in body["group"].keys()
        assert "name" in body["group"].keys()
        return 200, json_header, json.dumps({"errcode": 0, "errmsg": "ok"})

    responses.add_callback(responses.POST, UPDATE_URL, callback=update_group_callback)

    r = client.update_group("0", "test")
    assert r == {"errcode": 0, "errmsg": "ok"}

    def move_user_callback(request):
        body = json.loads(request.body.decode("utf-8"))
        assert "openid" in body.keys()
        assert "to_groupid" in body.keys()
        return 200, json_header, json.dumps({"errcode": 0, "errmsg": "ok"})

    responses.add_callback(responses.POST, MOVE_URL, callback=move_user_callback)

    r = client.move_user("test", "0")
    assert r == {"errcode": 0, "errmsg": "ok"}

    def move_users_callback(request):
        body = json.loads(request.body.decode("utf-8"))
        assert "openid_list" in body.keys()
        assert "to_groupid" in body.keys()
        return 200, json_header, json.dumps({"errcode": 0, "errmsg": "ok"})

    responses.add_callback(responses.POST, MOVE_USERS_URL, callback=move_users_callback)

    r = client.move_users("test", "test")
    assert r == {"errcode": 0, "errmsg": "ok"}

    def delete_group_callback(request):
        body = json.loads(request.body.decode("utf-8"))
        assert "group" in body.keys()
        assert "id" in body["group"].keys()
        return 200, json_header, json.dumps({"errcode": 0, "errmsg": "ok"})

    responses.add_callback(responses.POST, DELETE_URL, callback=delete_group_callback)

    r = client.delete_group("test")
    assert r == {"errcode": 0, "errmsg": "ok"}


@responses.activate
def test_client_remark():
    REMARK_URL = "https://api.weixin.qq.com/cgi-bin/user/info/updateremark"

    responses.add_callback(responses.GET, TOKEN_URL, callback=token_callback)
    config = Config()
    config.from_pyfile(os.path.join(basedir, "client_config.py"))
    client = Client(config)

    def remark_callback(request):
        body = json.loads(request.body.decode("utf-8"))
        assert "openid" in body.keys()
        assert "remark" in body.keys()
        return 200, json_header, json.dumps({"errcode": 0, "errmsg": "ok"})

    responses.add_callback(responses.POST, REMARK_URL, callback=remark_callback)

    r = client.remark_user("test", "test")
    assert r == {"errcode": 0, "errmsg": "ok"}


@responses.activate
def test_client_user_info():
    SINGLE_USER_URL = "https://api.weixin.qq.com/cgi-bin/user/info"
    MULTI_USER_URL = "https://api.weixin.qq.com/cgi-bin/user/info/batchget"

    responses.add_callback(responses.GET, TOKEN_URL, callback=token_callback)
    config = Config()
    config.from_pyfile(os.path.join(basedir, "client_config.py"))
    client = Client(config)

    def single_user_callback(request):
        params = urlparse.parse_qs(urlparse.urlparse(request.url).query)
        assert "access_token" in params.keys()
        assert "openid" in params.keys()
        assert "lang" in params.keys()
        return 200, json_header, json.dumps({"errcode": 0, "errmsg": "ok"})

    responses.add_callback(responses.GET, SINGLE_USER_URL, callback=single_user_callback)

    r = client.get_user_info("test")
    assert r == {"errcode": 0, "errmsg": "ok"}

    def multi_user_callback(request):
        body = json.loads(request.body.decode("utf-8"))
        assert "user_list" in body.keys()
        for user in body["user_list"]:
            assert "openid" in user.keys()
            assert "lang" in user.keys()
        return 200, json_header, json.dumps({"errcode": 0, "errmsg": "ok"})

    responses.add_callback(responses.POST, MULTI_USER_URL, callback=multi_user_callback)

    r = client.get_users_info(["test1", "test2"])
    assert r == {"errcode": 0, "errmsg": "ok"}


@responses.activate
def test_client_get_followers():
    FOLLOWER_URL = "https://api.weixin.qq.com/cgi-bin/user/get"

    responses.add_callback(responses.GET, TOKEN_URL, callback=token_callback)
    config = Config()
    config.from_pyfile(os.path.join(basedir, "client_config.py"))
    client = Client(config)

    def get_followers_callback(request):
        params = urlparse.parse_qs(urlparse.urlparse(request.url).query)
        assert "access_token" in params.keys()
        assert "next_openid" in params.keys()
        return 200, json_header, json.dumps({"errcode": 0, "errmsg": "ok"})

    responses.add_callback(responses.GET, FOLLOWER_URL, callback=get_followers_callback)

    r = client.get_followers("test")
    assert r == {"errcode": 0, "errmsg": "ok"}
