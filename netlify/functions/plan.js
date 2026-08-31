/**
 * Netlify Serverless Function: /.netlify/functions/plan
 */
exports.handler = async function(event, context) {
    const headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Content-Type": "application/json"
    };

    if (event.httpMethod === "OPTIONS") return { statusCode: 200, headers, body: "" };

    let body = {};
    try {
        body = JSON.parse(event.body || "{}");
    } catch(e) {}

    const country = body.country || "India";
    const industries = body.industries || [];

    const results = industries.map(ind => ({
        "Industry": ind,
        "Country": country,
        "Planned Slices": 1,
        "Estimated Coverage %": "100.0%",
        "Status": "Planned & Partitioned"
    }));

    return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ status: "success", results })
    };
};
