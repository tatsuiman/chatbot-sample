from fastapi import FastAPI
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from fastapi.openapi.utils import get_openapi
from intel import search_intelx, shodan_host

app = FastAPI()

# 除外するパス
excluded_paths = ["/docs", "/redoc", "/openapi.json", "/openai"]

# OpenAPIドキュメントを生成する関数
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Your API",
        version="1.0.0",
        description="API for intelligence tools",
        servers=[{"url": f"http://plugin:5000/"}],
        routes=app.routes,
    )
    # 設定の変更
    for path in excluded_paths:
        openapi_schema["paths"].pop(path, None)
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/openai")
async def openai_spec():
    return {
        "schema_version": "v1",
        "name_for_model": "Intelligence Tools",
        "name_for_human": "You",
        "description_for_human": "Intelligence tools api",
        "description_for_model": "Intelligence tools of shodan",
        "api": {
            "type": "openapi",
            "url": " http://plugin:5000/openapi.json",
            "has_user_authentication": False
        },
        "auth": {
            "type": "none"
        },
        "logo_url": "",
        "contact_email": "admin@example.com",
        "legal_info_url": "https://example.com"
    }

class IntelxRequest(BaseModel):
    term: str = Field(None, description="IP address or domain name or hash value")

class IntelxResult(BaseModel):
    added: Optional[str]
    name: Optional[str]
    data_source: Optional[str]
    tags: Optional[List[str]]
    type: Optional[str]

class IntelxResponse(BaseModel):
    total: int
    status: str
    results: List[IntelxResult]

@app.post("/intelx", description="Get cyber intelligence search result for a given IP address or domain or hash value")
async def intelx_endpoint(request: IntelxRequest):
    search_results = search_intelx(request.term)
    print(search_results)
    response_results = [IntelxResult(**result) for result in search_results["results"]]
    
    return IntelxResponse(
        total=search_results["total"],
        status=search_results["status"],
        results=response_results
    )


class ShodanRequest(BaseModel):
    term: str = Field(None, description="IP address or hostname")

class ShodanResult(BaseModel):
    city: Optional[str] = None
    country_name: Optional[str] = None
    region_code: Optional[str] = None
    os: Optional[str] = None
    tags: Optional[list[str]] = None
    ip: Optional[int] = None
    isp: Optional[str] = None
    area_code: Optional[str] = None
    longitude: Optional[float] = None
    last_update: Optional[str] = None
    ports: Optional[list[int]] = None
    latitude: Optional[float] = None
    hostnames: Optional[list[str]] = None
    country_code: Optional[str] = None
    vulns: Optional[list[str]] = None
    domains: Optional[list[str]] = None
    org: Optional[str] = None
    asn: Optional[str] = None
    ip_str: Optional[str] = None

@app.post("/shodan", description="Get Shodan search result for a given IP address or hostname")
async def shodan(item: ShodanRequest):
    result = shodan_host(item.term)
    return ShodanResult(**result)
