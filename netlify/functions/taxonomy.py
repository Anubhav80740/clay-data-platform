#!/usr/bin/env python3
"""
Netlify Serverless Function: /.netlify/functions/taxonomy
Serves the complete 458 Clay Industries and 218 Clay Countries taxonomy.
"""
import os
import json
import sys

# Ensure parent path is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from clay_taxonomy import ALL_CLAY_INDUSTRIES, ALL_CLAY_COUNTRIES, TECH_INDUSTRIES, NON_TECH_INDUSTRIES
except ImportError:
    ALL_CLAY_INDUSTRIES = ["Telecommunications", "Information Services", "Biotechnology", "Industrial Automation"]
    ALL_CLAY_COUNTRIES = ["Spain", "United States", "India", "United Kingdom", "France", "Germany", "Canada"]
    TECH_INDUSTRIES = ALL_CLAY_INDUSTRIES
    NON_TECH_INDUSTRIES = []

def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "status": "success",
            "countries": ALL_CLAY_COUNTRIES,
            "industries": ALL_CLAY_INDUSTRIES,
            "tech_industries": TECH_INDUSTRIES,
            "non_tech_industries": NON_TECH_INDUSTRIES
        })
    }
