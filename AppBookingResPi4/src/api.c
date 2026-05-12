#include "api.h"
#include "booking.h"
#include "storage.h"
#include "web.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define RESP_OK  "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n"
#define RESP_404 "HTTP/1.1 404 Not Found\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"ok\":false,\"error\":\"not found\"}"
#define RESP_400 "HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"ok\":false,\"error\":\"bad request\"}"
#define RESP_401 "HTTP/1.1 401 Unauthorized\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"ok\":false,\"error\":\"unauthorized\"}"
#define RESP_409 "HTTP/1.1 409 Conflict\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"ok\":false,\"error\":\"conflict\"}"
#define RESP_500 "HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{\"ok\":false,\"error\":\"internal error\"}"
#define ADMIN_PASSWORD "admin123"

int parse_json_string(const char *json, const char *key, char *out, size_t sz) {
    char pattern[64];
    const char *start;
    const char *end;
    size_t len;

    if (sz == 0) {
        return -1;
    }

    snprintf(pattern, sizeof(pattern), "\"%s\":\"", key);
    start = strstr(json, pattern);
    if (start == NULL) {
        out[0] = '\0';
        return -1;
    }
    start += strlen(pattern);
    end = strchr(start, '"');
    if (end == NULL) {
        out[0] = '\0';
        return -1;
    }

    len = (size_t)(end - start);
    if (len >= sz) {
        len = sz - 1;
    }
    memcpy(out, start, len);
    out[len] = '\0';
    return 0;
}

int parse_json_int(const char *json, const char *key, int *out) {
    char pattern[64];
    const char *start;
    char *endptr;
    long value;

    snprintf(pattern, sizeof(pattern), "\"%s\":", key);
    start = strstr(json, pattern);
    if (start == NULL) {
        return -1;
    }
    start += strlen(pattern);
    value = strtol(start, &endptr, 10);
    if (start == endptr) {
        return -1;
    }
    *out = (int)value;
    return 0;
}

int check_admin_password(const char *req) {
    return strstr(req, "X-Admin-Password: " ADMIN_PASSWORD) != NULL;
}

static void send_buf(int fd, const void *buf, size_t len) {
    ssize_t r = write(fd, buf, len); (void)r;
}
static void send_str(int fd, const char *s) { send_buf(fd, s, strlen(s)); }

static void handle_list_rooms(int fd) {
    Room *rooms = NULL;
    int count = 0;
    char body[8192];
    int pos;

    if (storage_room_list(&rooms, &count) != 0) {
        send_str(fd, RESP_500);
        return;
    }

    pos = snprintf(body, sizeof(body), "{\"ok\":true,\"data\":[");
    for (int i = 0; i < count; i++) {
        pos += snprintf(body + pos, sizeof(body) - (size_t)pos,
                        "%s{\"room_id\":%d,\"room_number\":\"%s\",\"room_type\":\"%s\",\"description\":\"%s\"}",
                        i > 0 ? "," : "",
                        rooms[i].room_id,
                        rooms[i].room_number,
                        rooms[i].room_type,
                        rooms[i].description);
    }
    pos += snprintf(body + pos, sizeof(body) - (size_t)pos, "]}");

    storage_room_free_list(rooms);
    send_str(fd, RESP_OK);
    send_buf(fd, body, (size_t)pos);
}

static void handle_availability(int fd, const char *path) {
    const char *qs;
    char check_in[12] = {0};
    char check_out[12] = {0};
    int *occupied_ids = NULL;
    int count = 0;
    char body[4096];
    int pos;

    qs = strchr(path, '?');
    if (qs == NULL) {
        send_str(fd, RESP_400);
        return;
    }
    qs++;

    if (sscanf(qs, "check_in=%11[^&]&check_out=%11s", check_in, check_out) != 2) {
        send_str(fd, RESP_400);
        return;
    }
    if (check_in[0] == '\0' || check_out[0] == '\0' || strcmp(check_in, check_out) >= 0) {
        send_str(fd, RESP_400);
        return;
    }
    if (storage_availability(check_in, check_out, &occupied_ids, &count) != 0) {
        send_str(fd, RESP_500);
        return;
    }

    pos = snprintf(body, sizeof(body), "{\"ok\":true,\"data\":{\"occupied\":[");
    for (int i = 0; i < count; i++) {
        pos += snprintf(body + pos, sizeof(body) - (size_t)pos,
                        "%s%d", i > 0 ? "," : "", occupied_ids[i]);
    }
    pos += snprintf(body + pos, sizeof(body) - (size_t)pos, "]}}");

    free(occupied_ids);
    send_str(fd, RESP_OK);
    send_buf(fd, body, (size_t)pos);
}

static void handle_book(int fd, const char *body) {
    Booking booking;
    char response[256];
    int booking_id;
    int pos;

    memset(&booking, 0, sizeof(booking));
    if (parse_json_string(body, "guest_name", booking.guest_name, sizeof(booking.guest_name)) != 0 ||
        parse_json_string(body, "email", booking.email, sizeof(booking.email)) != 0 ||
        parse_json_string(body, "check_in", booking.check_in_date, sizeof(booking.check_in_date)) != 0 ||
        parse_json_string(body, "check_out", booking.check_out_date, sizeof(booking.check_out_date)) != 0 ||
        parse_json_int(body, "guests", &booking.number_of_guests) != 0 ||
        parse_json_int(body, "room_id", &booking.room_id) != 0) {
        send_str(fd, RESP_400);
        return;
    }

    if (booking.guest_name[0] == '\0' || booking.email[0] == '\0' ||
        booking.check_in_date[0] == '\0' || booking.check_out_date[0] == '\0' ||
        booking.number_of_guests < 1 || strcmp(booking.check_in_date, booking.check_out_date) >= 0 ||
        booking.room_id <= 0) {
        send_str(fd, RESP_400);
        return;
    }

    booking_id = booking_create(&booking);
    if (booking_id == -2) {
        send_str(fd, RESP_409);
        return;
    }
    if (booking_id < 0) {
        send_str(fd, RESP_500);
        return;
    }

    pos = snprintf(response, sizeof(response), "{\"ok\":true,\"data\":{\"booking_id\":%d}}", booking_id);
    send_str(fd, RESP_OK);
    send_buf(fd, response, (size_t)pos);
}

static void handle_admin_list(int fd, const char *req) {
    Booking *list = NULL;
    int count = 0;
    char body[16384];
    int pos;

    if (!check_admin_password(req)) {
        send_str(fd, RESP_401);
        return;
    }
    if (booking_list(&list, &count) != 0) {
        send_str(fd, RESP_500);
        return;
    }

    pos = snprintf(body, sizeof(body), "{\"ok\":true,\"data\":[");
    for (int i = 0; i < count; i++) {
        pos += snprintf(body + pos, sizeof(body) - (size_t)pos,
                        "%s{\"booking_id\":%d,\"guest_name\":\"%s\",\"email\":\"%s\","
                        "\"room_number\":\"%s\",\"room_type\":\"%s\",\"check_in_date\":\"%s\","
                        "\"check_out_date\":\"%s\",\"number_of_guests\":%d,\"created_at\":%lld,"
                        "\"status\":\"%s\"}",
                        i > 0 ? "," : "",
                        list[i].booking_id,
                        list[i].guest_name,
                        list[i].email,
                        list[i].room_number,
                        list[i].room_type,
                        list[i].check_in_date,
                        list[i].check_out_date,
                        list[i].number_of_guests,
                        (long long)list[i].created_at,
                        list[i].status);
    }
    pos += snprintf(body + pos, sizeof(body) - (size_t)pos, "]}");

    booking_free_list(list);
    send_str(fd, RESP_OK);
    send_buf(fd, body, (size_t)pos);
}

static void handle_admin_cancel(int fd, const char *req, int booking_id) {
    static const char response[] = "{\"ok\":true}";

    if (!check_admin_password(req)) {
        send_str(fd, RESP_401);
        return;
    }
    if (booking_cancel(booking_id) != 0) {
        send_str(fd, RESP_404);
        return;
    }

    send_str(fd, RESP_OK);
    send_buf(fd, response, sizeof(response) - 1);
}

void api_handle(int fd, const char *req, size_t len) {
    (void)len;
    char method[8], path[256];
    const char *body;
    int booking_id;
    sscanf(req, "%7s %255s", method, path);
    body = strstr(req, "\r\n\r\n");
    if (body != NULL) {
        body += 4;
    } else {
        body = "";
    }

    if (strcmp(path, "/") == 0 ||
        strcmp(path, "/admin") == 0 ||
        strcmp(path, "/vendor/css/core.css") == 0 ||
        strcmp(path, "/vendor/js/bootstrap.js") == 0 ||
        strcmp(path, "/vendor/js/helpers.js") == 0 ||
        strcmp(path, "/vendor/js/menu.js") == 0) {
        web_serve(fd, path);
        return;
    }
    if (strcmp(path, "/api/rooms") == 0 && strcmp(method, "GET") == 0) {
        handle_list_rooms(fd);
        return;
    }
    if (strncmp(path, "/api/availability", 17) == 0 && strcmp(method, "GET") == 0) {
        handle_availability(fd, path);
        return;
    }
    if (strcmp(path, "/api/book") == 0 && strcmp(method, "POST") == 0) {
        handle_book(fd, body);
        return;
    }
    if (strcmp(path, "/api/bookings") == 0 && strcmp(method, "GET") == 0) {
        handle_admin_list(fd, req);
        return;
    }
    if (sscanf(path, "/api/bookings/%d", &booking_id) == 1 && strcmp(method, "DELETE") == 0) {
        handle_admin_cancel(fd, req, booking_id);
        return;
    }
    send_str(fd, RESP_404);
}
