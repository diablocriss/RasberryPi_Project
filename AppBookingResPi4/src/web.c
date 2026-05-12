#include "web.h"
#include "index_html.h"
#include "admin_html.h"
#include "vendor_core_css.h"
#include "vendor_bootstrap_js.h"
#include "vendor_helpers_js.h"
#include "vendor_menu_js.h"
#include <stdio.h>
#include <string.h>
#include <unistd.h>

void web_serve(int fd, const char *path) {
    const unsigned char *html = index_html;
    unsigned int html_len = index_html_len;
    const char *content_type = "text/html; charset=utf-8";
    char header[256];

    if (strcmp(path, "/admin") == 0) {
        html = admin_html;
        html_len = admin_html_len;
    } else if (strcmp(path, "/vendor/css/core.css") == 0) {
        html = vendor_core_css;
        html_len = vendor_core_css_len;
        content_type = "text/css";
    } else if (strcmp(path, "/vendor/js/bootstrap.js") == 0) {
        html = vendor_bootstrap_js;
        html_len = vendor_bootstrap_js_len;
        content_type = "application/javascript";
    } else if (strcmp(path, "/vendor/js/helpers.js") == 0) {
        html = vendor_helpers_js;
        html_len = vendor_helpers_js_len;
        content_type = "application/javascript";
    } else if (strcmp(path, "/vendor/js/menu.js") == 0) {
        html = vendor_menu_js;
        html_len = vendor_menu_js_len;
        content_type = "application/javascript";
    }

    int hlen = snprintf(header, sizeof(header),
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: %s\r\n"
        "Content-Length: %u\r\n"
        "Connection: close\r\n\r\n",
        content_type, html_len);
    ssize_t r;
    r = write(fd, header, hlen);
    (void)r;
    r = write(fd, html, html_len);
    (void)r;
}
