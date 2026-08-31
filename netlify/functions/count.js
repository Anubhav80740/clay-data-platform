/**
 * Netlify Serverless Function: /.netlify/functions/count
 * Ultra-fast native Node.js parallel count queries against Clay API.
 */

const WORKSPACE_ID = "744216";
const FRONTEND_VERSION = "v20260830_143110Z_acbd7caddc";
const DEFAULT_COOKIE = "marketing_ajs_anonymous_id=DEBUG_B; _ga=GA1.1.203504950.1785217902; claysession=s%3AirV0NOBrZHfl0XdJLdsdYi1wECnh-nbR.gbhu3335fWNG72Zl0fH85wI%2FuoAJlM1SRP5oKr3%2FUFA; intercom-device-id-w28k1kwz=d424c801-aa75-4f80-bcfc-998b90dd88b6; _ga_NHFD0GLCLV=GS2.1.s1788176390$o6$g1$t1788176396$j54$l0$h0$dp_PDvBVKSoP-8tSn0HhEGiV26xiM4MPy3Q";

exports.handler = async function(event, context) {
    const corsHeaders = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Content-Type": "application/json"
    };

    if (event.httpMethod === "OPTIONS") {
        return { statusCode: 200, headers: corsHeaders, body: "" };
    }

    let body = {};
    try {
        body = typeof event.body === 'string' ? JSON.parse(event.body || "{}") : (event.body || {});
    } catch (e) {
        body = {};
    }

    const country = body.country || "India";
    const industries = body.industries || [];
    const entityType = body.entityType || "companies";

    if (!industries.length) {
        return {
            statusCode: 200,
            headers: corsHeaders,
            body: JSON.stringify({ status: "success", results: [], total_count: 0 })
        };
    }

    const cookie = process.env.CLAY_COOKIE || DEFAULT_COOKIE;
    const clayHeaders = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "cookie": cookie,
        "origin": "https://app.clay.com",
        "referer": "https://app.clay.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        "x-clay-frontend-version": FRONTEND_VERSION
    };

    const url = `https://api.clay.com/v3/workspaces/${WORKSPACE_ID}/actions/run-cpj-preview-enrichment`;

    const fetchSingle = async (ind) => {
        try {
            const payload = (entityType === "people") ? {
                enrichmentType: "find-lists-of-people-with-mixrank-source-preview",
                options: { returnTaskId: true, returnActionMetadata: true },
                inputs: {
                    company_industries_include: [ind],
                    location_countries_include: [country],
                    limit: 1,
                    result_count: true
                }
            } : {
                enrichmentType: "find-lists-of-companies-with-mixrank-source-preview",
                options: { returnTaskId: true, returnActionMetadata: true },
                inputs: {
                    country_names: [country],
                    industries: [ind],
                    limit: 1,
                    result_count: true
                }
            };

            const resp = await fetch(url, {
                method: "POST",
                headers: clayHeaders,
                body: JSON.stringify(payload)
            });

            if (resp.ok) {
                const data = await resp.json();
                const cnt = (entityType === "people") ? data.result?.peopleCount : data.result?.companyCount;
                return {
                    "Industry": ind,
                    "Target Country": country,
                    "Entity Type": (entityType === "people" ? "People" : "Companies"),
                    "Exact Clay Target Count": cnt !== undefined ? cnt : 0
                };
            }
        } catch (e) {
            console.error("Fetch single error:", e);
        }

        return {
            "Industry": ind,
            "Target Country": country,
            "Entity Type": (entityType === "people" ? "People" : "Companies"),
            "Exact Clay Target Count": 0
        };
    };

    try {
        const results = await Promise.all(industries.map(ind => fetchSingle(ind)));
        const totalCount = results.reduce((acc, r) => acc + (r["Exact Clay Target Count"] || 0), 0);

        return {
            statusCode: 200,
            headers: corsHeaders,
            body: JSON.stringify({
                status: "success",
                results: results,
                total_count: totalCount,
                industries_count: results.length
            })
        };
    } catch (err) {
        return {
            statusCode: 500,
            headers: corsHeaders,
            body: JSON.stringify({ status: "error", message: err.message })
        };
    }
};
