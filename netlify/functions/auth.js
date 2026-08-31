/**
 * Netlify Serverless Function: /.netlify/functions/auth
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

    const user = (body.user || "").trim();
    const pass = (body.pass || "").trim();

    const teamUser = process.env.CLAY_USER_ID || "team";
    const teamPass = process.env.CLAY_PASSWORD || "clay2026";

    if (user === teamUser && pass === teamPass) {
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({ status: "success", user })
        };
    } else {
        return {
            statusCode: 401,
            headers,
            body: JSON.stringify({ status: "error", message: "Invalid credentials" })
        };
    }
};
