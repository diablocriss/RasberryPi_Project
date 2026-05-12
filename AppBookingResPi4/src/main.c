#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "server.h"
#include "storage.h"

static void usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s [options]\n"
        "  -p <port>    HTTP port to listen on (default: 8080)\n"
        "  -d <path>    SQLite database path (default: bookings.db)\n"
        "  -h           Show this help\n",
        prog);
}

int main(int argc, char *argv[]) {
    int port = 8080;
    const char *db_path = "bookings.db";
    int opt;

    while ((opt = getopt(argc, argv, "p:d:h")) != -1) {
        switch (opt) {
            case 'p': port = atoi(optarg); break;
            case 'd': db_path = optarg;    break;
            case 'h': usage(argv[0]); return 0;
            default:  usage(argv[0]); return 1;
        }
    }

    if (storage_init(db_path) != 0) {
        fprintf(stderr, "Failed to open database: %s\n", db_path);
        return 1;
    }

    printf("AppBookingRes listening on http://0.0.0.0:%d\n", port);
    printf("Database: %s\n", db_path);

    server_run(port);

    storage_close();
    return 0;
}
