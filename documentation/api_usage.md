# OpsDeck API Usage Guide

This guide provides instructions on how to access and authenticate with the OpsDeck REST API.

## 1. Authentication
The API uses **Bearer Token** authentication. You must include your personal API token in the `Authorization` header of every request.

### Getting a Token
1.  Log in to the OpsDeck application.
2.  Navigate to **User Management** -> **Users**.
3.  Click on your user profile (or the user you wish to generate a token for).
4.  Scroll down to the **Developer Settings (API)** section.
5.  Click **Generate New Token**.
6.  Copy the generated token.

> **Security Note:** Treat this token like a password. If compromised, regenerate it immediately to invalidate the old one.

## 2. API Documentation (Swagger UI)
The API is self-documenting. You can explore all available endpoints, schemas, and test requests directly in your browser.

*   **URL:** `/swagger-ui` (e.g., `http://localhost:5000/swagger-ui`)
*   **OpenAPI Spec:** `/openapi.json`

### Using Swagger UI
1.  Click the **Authorize** button at the top right.
2.  Enter your token in the value field: `Bearer <your_token_here>`.
3.  Click **Authorize** and then **Close**.
4.  You can now click "Try it out" on any endpoint to execute requests.

## 3. Querying the API
All API endpoints are prefixed with `/api/v1`.

### Curl Examples

**List all Assets:**
```bash
curl -X GET "http://localhost:5000/api/v1/assets" \
     -H "Authorization: Bearer <your_token_here>" \
     -H "Accept: application/json"
```

**Get a Specific User:**
```bash
curl -X GET "http://localhost:5000/api/v1/users/1" \
     -H "Authorization: Bearer <your_token_here>" \
     -H "Accept: application/json"
```

**Pagination:**
You can paginate results using the `page` and `page_size` query parameters.
```bash
curl -X GET "http://localhost:5000/api/v1/assets?page=2&page_size=5" \
     -H "Authorization: Bearer <your_token_here>"
```

## 4. Error Handling
The API returns standard HTTP status codes:
*   `200 OK`: Success.
*   `401 Unauthorized`: Missing or invalid token.
*   `404 Not Found`: Resource not found.
*   `429 Too Many Requests`: Rate limit exceeded.
