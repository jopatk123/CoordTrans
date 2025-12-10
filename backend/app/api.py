from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import io
from fastapi.responses import StreamingResponse
from .services import amap_service

router = APIRouter()

class GeoRequest(BaseModel):
    address: str
    city: Optional[str] = None

class RegeoRequest(BaseModel):
    location: str # lon,lat

@router.post("/geo")
async def geocode(req: GeoRequest):
    result = await amap_service.geo_code(req.address, req.city)
    if not result:
        return {"status": "failed", "msg": "Not found"}
    return {"status": "success", "data": result}

@router.post("/regeo")
async def regeocode(req: RegeoRequest):
    result = await amap_service.regeo_code(req.location, extensions="all")
    if not result:
        return {"status": "failed", "msg": "Not found"}
    return {"status": "success", "data": result}

@router.post("/batch/file/geo")
async def batch_file_geo(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(400, "Unsupported file format. Please upload CSV or Excel.")
    except Exception as e:
        raise HTTPException(400, f"Error reading file: {str(e)}")
    
    # Find address column
    target_col = None
    for col in df.columns:
        if "address" in str(col).lower() or "地址" in str(col):
            target_col = col
            break
    if target_col is None:
        target_col = df.columns[0] # Default to first column

    addresses = df[target_col].astype(str).tolist()
    # Limit batch size for safety
    if len(addresses) > 1000:
        raise HTTPException(400, "Batch size limit exceeded (max 1000 rows)")

    results = await amap_service.batch_geo_code(addresses)
    
    lons, lats, formatted_addresses, provinces, cities, districts = [], [], [], [], [], []
    
    for res in results:
        if res:
            loc = res.get('location', ',').split(',')
            lons.append(loc[0] if len(loc) > 0 else '')
            lats.append(loc[1] if len(loc) > 1 else '')
            formatted_addresses.append(res.get('formatted_address', ''))
            provinces.append(res.get('province', ''))
            cities.append(res.get('city', ''))
            districts.append(res.get('district', ''))
        else:
            lons.append('')
            lats.append('')
            formatted_addresses.append('')
            provinces.append('')
            cities.append('')
            districts.append('')
            
    df['api_longitude'] = lons
    df['api_latitude'] = lats
    df['api_formatted_address'] = formatted_addresses
    df['api_province'] = provinces
    df['api_city'] = cities
    df['api_district'] = districts
    
    output = io.BytesIO()
    # Default to Excel for output
    df.to_excel(output, index=False)
    output.seek(0)
    
    return StreamingResponse(
        output, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=processed_geocoding.xlsx"}
    )

@router.post("/batch/file/regeo")
async def batch_file_regeo(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(400, "Unsupported file format")
    except Exception:
        raise HTTPException(400, "Error reading file")

    # Find lat/lon columns
    lat_col, lon_col = None, None
    for col in df.columns:
        c = str(col).lower()
        if "lat" in c or "纬度" in c: lat_col = col
        if "lon" in c or "lng" in c or "经度" in c: lon_col = col
    
    if not lat_col or not lon_col:
        # Try first two columns
        if len(df.columns) >= 2:
            lon_col, lat_col = df.columns[0], df.columns[1]
        else:
            raise HTTPException(400, "Could not identify Latitude/Longitude columns")

    locations = []
    for _, row in df.iterrows():
        locations.append(f"{row[lon_col]},{row[lat_col]}")

    if len(locations) > 1000:
        raise HTTPException(400, "Batch size limit exceeded (max 1000 rows)")

    results = await amap_service.batch_regeo_code(locations)
    
    addrs = []
    townships = []
    
    for res in results:
        if res:
            addrs.append(res.get('formatted_address', ''))
            addr_comp = res.get('addressComponent', {})
            townships.append(addr_comp.get('township', ''))
        else:
            addrs.append('')
            townships.append('')
            
    df['api_address'] = addrs
    df['api_township'] = townships
    
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    
    return StreamingResponse(
        output, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=processed_regeocoding.xlsx"}
    )
