from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS config: replace with actual allowed origins for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "https://your-android-app.com"],  # ← specify exact origins
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

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Get access token
            token_resp = await client.post(
                "https://api.insee.fr/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "client_credentials"},
                auth=httpx.BasicAuth(client_id, client_secret)
            )

            if token_resp.status_code != 200:
                logger.error("Token fetch failed: %s", token_resp.text)
                raise HTTPException(status_code=token_resp.status_code, detail="Token fetch failed")

            access_token = token_resp.json().get("access_token")
            if not access_token:
                raise HTTPException(status_code=500, detail="No access token in response")

            # Step 2: Query the SIRET
            insee_resp = await client.get(
                f"https://api.insee.fr/entreprises/sirene/V3/siret/{siret}?champs=uniteLegale",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if insee_resp.status_code != 200:
                logger.error("INSEE API error: %s", insee_resp.text)
                raise HTTPException(status_code=insee_resp.status_code, detail="Sirene lookup failed")

            etab = insee_resp.json().get("etablissement", {}).get("uniteLegale", {})

            return {
                "nafCode": etab.get("activitePrincipale", ""),
                "nafLabel": etab.get("nomenclatureActivitePrincipale", ""),
                "name": etab.get("denominationUniteLegale", "")
            }
    except httpx.HTTPError as e:
        logger.exception("HTTP client error")
        raise HTTPException(status_code=500, detail="External API call failed")
