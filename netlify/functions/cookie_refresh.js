/**
 * Netlify Serverless Function: /.netlify/functions/cookie_refresh
 */
exports.handler = async function(event, context) {
    const headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json"
    };

    return {
        statusCode: 200,
        headers,
        body: JSON.stringify({
            status: "success",
            provider: "netlify-node",
            has_cookie: true
        })
    };
};
