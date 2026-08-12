import logging
from Base.Config.logConfig import setup_logging
from Analyzer.router.router import init_router

# 日志配置初始化
setup_logging()

logger = logging.getLogger(__name__)
from Analyzer.frontend.fastapi_init import frontend_init

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger.info("启动自Analyzer包")
app = FastAPI()

# 必填参数缺失/格式错误时返回友好中文提示（FastAPI 默认 422 的 detail 是英文数组）
_VALIDATION_FIELD_LABELS = {
    "receive_email": "接收邮箱",
    "user_name": "用户名",
    "company_name": "公司名称",
    "audio_file": "音频文件",
    "resume_file": "简历文件",
}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first = errors[0] if errors else {}
    loc = first.get("loc", [])
    raw_field = str(loc[-1]) if loc else "参数"
    field = _VALIDATION_FIELD_LABELS.get(raw_field, raw_field)
    if first.get("type") == "missing":
        msg = f"缺少必填项: {field}"
    else:
        msg = f"{field} 校验失败: {first.get('msg', '格式错误')}"
    return JSONResponse(status_code=422, content={"msg": msg})
# 初始化前端
frontend_init(app=app)
init_router(app=app)





if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app=app, host="0.0.0.0", port=8000)