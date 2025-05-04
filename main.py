from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI()

# Allow calls from your Android app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/siret/{siret}")
async def get_sirene_data(siret: str):
    client_id = os.getenv("INSEE_CLIENT_ID")
    client_secret = os.getenv("INSEE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="API credentials missing")

    async with httpx.AsyncClient() as client:
        # 1. Get access token
        token_response = await client.post(
            "https://api.insee.fr/token",
            data={"grant_type": "client_credentials"},
            auth=httpx.BasicAuth(client_id, client_secret)
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=token_response.status_code, detail="Token fetch failed")

        access_token = token_response.json().get("access_token")

        # 2. Fetch SIRET data
api_response = await client.get(
    f"https://api.insee.fr/entreprises/sirene/V3/siret/{siret}?champs=uniteLegale",
    headers={"Authorization": f"Bearer {access_token}"}
)

        if api_response.status_code != 200:
            # DEBUG: log full response text to Render logs
            print("INSEE error:", api_response.status_code, api_response.text)
            raise HTTPException(status_code=api_response.status_code, detail="Sirene lookup failed")

        data = api_response.json()
        etab = data.get("etablissement", {}).get("uniteLegale", {})

        return {
            "nafCode": etab.get("activitePrincipale", ""),
            "nafLabel": etab.get("nomenclatureActivitePrincipale", ""),
            "name": etab.get("denominationUniteLegale", "")
        }
