// CloudFront Function on the default behaviour (B3-04, B3 decision 2).
//
// The React app has one HTML file. A visit to /todos or a reload on /journal/2026-11-20
// asks S3 for a file that does not exist. This function sends every path whose last
// part has no dot (no file extension) to /index.html; React Router then shows the right
// screen. Files such as /assets/index-abc123.js are passed through unchanged.
//
// It never sees /api/* requests: those go to the API behaviour, which has no function.
// That is why this is better than CloudFront's "custom error response" trick, which
// would also turn API errors into the React page.
//
// Runtime cloudfront-js-2.0: a small JavaScript engine with a 1 ms time limit, so the
// code stays tiny and has no imports.

function handler(event) {
  var request = event.request;
  var lastPart = request.uri.substring(request.uri.lastIndexOf("/") + 1);

  if (lastPart.indexOf(".") === -1) {
    request.uri = "/index.html";
  }

  return request;
}
