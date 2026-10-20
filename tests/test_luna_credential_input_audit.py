"""No real credential, clipboard, socket, console or provider required."""
from datetime import timedelta
from io import StringIO
import json
import httpx
import pytest
from pydantic import SecretStr
from api.llm.contract import LLMInvocationError
from scripts import luna_credential_supervisor as s
from scripts.evaluate_openai_luna_low_live import OpenAIResponsesAdapter, credential_problem
from test_openai_luna_low_live import _request
from test_luna_credential_supervisor import lease

TOKEN = 'sk-' + 'synthetic-only-audit-value'


def read(sequence):
    sequence=iter(sequence);screen=StringIO()
    value=s.read_credential(s.now()+timedelta(seconds=30),s.time.monotonic()+30,
                            read_char=lambda:next(sequence),write=screen.write)
    assert TOKEN not in screen.getvalue()
    return value,screen.getvalue()


def test_asterisks_and_count_never_echo_key():
    value,screen=read(TOKEN+'\r')
    assert value==TOKEN and '*'*min(len(TOKEN),32) in screen
    assert f'[{len(TOKEN)} caracteres]' in screen
    assert 'autenticacao na API ainda nao verificada' in screen


def test_duplicate_paste_is_discarded_and_can_be_corrected():
    value,screen=read(TOKEN*2+'\r'+TOKEN+'\r')
    assert value==TOKEN and 'colagem repetida' in screen


@pytest.mark.parametrize('clear',['\x1b','\x15'])
def test_clear_discards_bad_input_without_revealing_it(clear):
    value,_=read('wrong'+clear+TOKEN+'\r')
    assert value==TOKEN


def test_backspace_corrects_input():
    assert read(TOKEN+'x\b\r')[0]==TOKEN


def test_bare_ctrl_v_is_not_an_http_header_character():
    value,screen=read('\x16\r'+TOKEN+'\r')
    assert value==TOKEN and 'Entrada invalida' in screen


def test_unicode_is_never_echoed_or_silently_sanitized():
    value,screen=read(TOKEN+'é\r'+TOKEN+'\r')
    assert value==TOKEN and 'é' not in screen and 'Entrada invalida' in screen


def test_cancel_does_not_return_a_key():
    with pytest.raises(KeyboardInterrupt):read(TOKEN+'\x03')


def test_overlong_input_is_rejected_not_silently_truncated():
    value,screen=read('x'*4097+'\r'+TOKEN+'\r')
    assert value==TOKEN and 'Entrada invalida' in screen


def test_expiry_during_character_read_never_confirms_success(monkeypatch):
    expires=s.now()+timedelta(seconds=10);deadline=s.time.monotonic()+10
    output=StringIO();clock=[s.now()]
    monkeypatch.setattr(s,'now',lambda:clock[0])
    def delayed_enter():clock[0]=expires+timedelta(seconds=1);return '\r'
    with pytest.raises(ValueError,match='lease_expired'):
        s.read_credential(expires,deadline,read_char=delayed_enter,write=output.write)
    assert 'Formato local validado' not in output.getvalue()


@pytest.mark.parametrize('value,problem',[
    ('','missing'),(TOKEN,None),(TOKEN*2,'repeated'),(TOKEN*3,'repeated'),
    (TOKEN+'\x16','invalid_characters'),(' '+TOKEN,'invalid_characters'),
    (TOKEN+'\r\n','invalid_characters'),(TOKEN+'é','invalid_characters'),
])
def test_local_validation_has_no_secret_in_diagnostic(value,problem):
    assert credential_problem(value)==problem


@pytest.mark.asyncio
@pytest.mark.parametrize('value',[TOKEN*2,TOKEN+'\x16',' '+TOKEN,TOKEN+'é'])
async def test_bad_credential_is_rejected_before_http(value):
    async def forbidden(_request):pytest.fail('must reject before transport')
    adapter=OpenAIResponsesAdapter(base_url='https://invalid.test/v1',capability_set=None,
        api_key=SecretStr(value),reasoning_effort='low',transport=httpx.MockTransport(forbidden))
    with pytest.raises(LLMInvocationError) as caught:await adapter.generate_structured(_request())
    assert caught.value.error.code=='credential_input_invalid'
    assert TOKEN not in caught.value.error.model_dump_json()


@pytest.mark.asyncio
async def test_empty_key_uses_existing_validation_phase_instead_of_attribute_error():
    async def forbidden(_request):pytest.fail('no HTTP for missing key')
    adapter=OpenAIResponsesAdapter(base_url='https://invalid.test/v1',capability_set=None,
        api_key=SecretStr(''),reasoning_effort='low',transport=httpx.MockTransport(forbidden))
    with pytest.raises(LLMInvocationError) as caught:await adapter.generate_structured(_request())
    assert caught.value.error.code=='credential_missing'
    assert caught.value.error.phase.value=='validation'


@pytest.mark.asyncio
@pytest.mark.parametrize('status',[401,403,429,500])
async def test_http_status_preserved_without_response_body(status):
    async def respond(_request):return httpx.Response(status,json={'error':{'message':TOKEN}})
    adapter=OpenAIResponsesAdapter(base_url='https://invalid.test/v1',capability_set=None,
        api_key=SecretStr(TOKEN),reasoning_effort='low',transport=httpx.MockTransport(respond))
    with pytest.raises(LLMInvocationError) as caught:await adapter.generate_structured(_request())
    assert caught.value.error.code==f'http_{status}'
    assert TOKEN not in caught.value.error.model_dump_json()


@pytest.mark.asyncio
@pytest.mark.parametrize('error_type,code',[
    (httpx.LocalProtocolError,'local_protocol_invalid'),
    (httpx.ConnectError,'transport_connection_failed'),
    (httpx.ReadTimeout,'transport_timeout'),
    (httpx.RemoteProtocolError,'remote_protocol_invalid'),
    (ValueError,'local_request_invalid'),
])
async def test_transport_categories_do_not_log_exception_messages(error_type,code):
    calls=[]
    async def fail(_request):
        calls.append(1);raise error_type(TOKEN+' synthetic sensitive exception')
    adapter=OpenAIResponsesAdapter(base_url='https://invalid.test/v1',capability_set=None,
        api_key=SecretStr(TOKEN),reasoning_effort='low',transport=httpx.MockTransport(fail))
    with pytest.raises(LLMInvocationError) as caught:await adapter.generate_structured(_request())
    assert caught.value.error.code==code and calls==[1]
    assert TOKEN not in caught.value.error.model_dump_json()


@pytest.mark.asyncio
@pytest.mark.parametrize('content,code',[(b'<html>not json</html>','response_json_invalid'),
                                       (b'[]','response_shape_invalid')])
async def test_response_failure_is_not_confused_with_transport(content,code):
    async def respond(_request):return httpx.Response(200,content=content)
    adapter=OpenAIResponsesAdapter(base_url='https://invalid.test/v1',capability_set=None,
        api_key=SecretStr(TOKEN),reasoning_effort='low',transport=httpx.MockTransport(respond))
    with pytest.raises(LLMInvocationError) as caught:await adapter.generate_structured(_request())
    assert caught.value.error.code==code


def test_ctrl_v_header_failure_is_reproducible_without_network():
    import h11
    with pytest.raises(h11.LocalProtocolError):
        h11.Request(method=b'POST',target=b'/',headers=[(b'Authorization',b'Bearer synthetic'+b'\x16')])


@pytest.mark.asyncio
async def test_supervisor_rejects_bad_key_before_spawning(lease,monkeypatch):
    root,_,request,expires,deadline=lease
    monkeypatch.setattr(s.subprocess,'Popen',lambda *_a,**_kw:pytest.fail('no subprocess'))
    with pytest.raises(ValueError,match='credential_input_invalid'):
        s.dispatch(request,TOKEN*2,expires,deadline,root=root)
