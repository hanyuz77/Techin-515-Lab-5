"""GIX Asset Tool — Streamlit app for logging assets to Supabase."""

import csv
import io
import os
import re

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

import streamlit as st
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

CATEGORIES = ("IT", "Makerspace")
LOCATIONS = ("IT shop", "Makerspace")
DEFAULT_STATUS = "Active"


def clean_name_from_raw(raw: str) -> str:
    words = raw.strip().split()
    return " ".join(words[:6]) if words else ""


def validate_asset_tag(tag: str) -> str | None:
    t = tag.strip()
    if re.fullmatch(r"\d{8}", t):
        return t
    return None


@st.cache_resource
def get_supabase():
    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            return None, "SUPABASE_URL and SUPABASE_KEY must be set in your .env file."
        return create_client(url.strip(), key.strip()), None
    except Exception as e:
        return None, f"Could not initialize Supabase: {e}"


def main():
    st.set_page_config(page_title="GIX Asset Tool", layout="wide")
    st.title("GIX Asset Tool")

    client, err = get_supabase()
    if client is None:
        st.error(err or "Unable to connect to Supabase.")
        st.stop()

    st.subheader("Add asset")
    raw_name = st.text_area(
        "Raw Amazon product description",
        placeholder="Paste the full product title or description…",
        height=150,
    )
    asset_tag_input = st.text_input(
        "Asset tag",
        placeholder="8-digit number",
        help="Exactly 8 digits.",
    )
    category = st.selectbox("Category", CATEGORIES)
    location = st.selectbox("Location", LOCATIONS)

    if st.button("Save to Supabase", type="primary"):
        tag = validate_asset_tag(asset_tag_input)
        if not raw_name.strip():
            st.warning("Please paste a raw product description.")
        elif tag is None:
            st.warning("Asset tag must be exactly 8 digits.")
        else:
            clean = clean_name_from_raw(raw_name)
            if not clean:
                st.warning("Could not derive a short name from the description.")
            else:
                try:
                    client.table("assets").insert(
                        {
                            "asset_tag": tag,
                            "raw_name": raw_name.strip(),
                            "clean_name": clean,
                            "category": category,
                            "status": DEFAULT_STATUS,
                            "location": location,
                        }
                    ).execute()
                    st.success("Asset saved successfully.")
                    st.rerun()
                except Exception as e:
                    st.error(
                        "We could not save this asset. Check your connection, "
                        "table permissions, and that the asset tag is unique. "
                        f"Details: {e}"
                    )

    st.divider()
    st.subheader("Saved assets")

    try:
        response = (
            client.table("assets")
            .select(
                "id, asset_tag, raw_name, clean_name, category, status, location, created_at"
            )
            .order("created_at", desc=True)
            .execute()
        )
        rows = response.data or []
    except Exception as e:
        st.error(
            "We could not load assets from the database. "
            f"Please try again later. Details: {e}"
        )
        rows = []

    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No assets yet, or the list is empty.")

    st.divider()
    st.subheader("Export")

    csv_columns = ["asset_tag", "clean_name", "category", "status", "location"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=csv_columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: row.get(c, "") for c in csv_columns})
    csv_text = buf.getvalue()

    st.download_button(
        label="Download all assets (CSV)",
        data=csv_text,
        file_name="assets_export.csv",
        mime="text/csv",
        disabled=not csv_text,
    )


if __name__ == "__main__":
    main()
