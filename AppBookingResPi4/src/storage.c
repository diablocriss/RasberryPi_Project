#include "storage.h"
#include <pthread.h>
#include <sqlite3.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static sqlite3 *db;
static pthread_mutex_t db_lock = PTHREAD_MUTEX_INITIALIZER;

static const char *SCHEMA =
    "CREATE TABLE IF NOT EXISTS rooms ("
    "  room_id      INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  room_number  TEXT    NOT NULL UNIQUE,"
    "  room_type    TEXT    NOT NULL,"
    "  description  TEXT    DEFAULT ''"
    ");"
    "CREATE TABLE IF NOT EXISTS bookings ("
    "  booking_id        INTEGER PRIMARY KEY AUTOINCREMENT,"
    "  guest_name        TEXT    NOT NULL,"
    "  email             TEXT    NOT NULL,"
    "  check_in_date     TEXT    NOT NULL,"
    "  check_out_date    TEXT    NOT NULL,"
    "  number_of_guests  INTEGER NOT NULL DEFAULT 1,"
    "  room_id           INTEGER NOT NULL REFERENCES rooms(room_id),"
    "  created_at        INTEGER NOT NULL,"
    "  status            TEXT    NOT NULL DEFAULT 'active'"
    ");";

static void copy_text(char *dst, size_t dst_sz, const unsigned char *src) {
    if (dst_sz == 0) {
        return;
    }
    if (src == NULL) {
        dst[0] = '\0';
        return;
    }
    snprintf(dst, dst_sz, "%s", (const char *)src);
}

static int storage_seed_rooms(void) {
    static const struct {
        const char *room_number;
        const char *room_type;
        const char *description;
    } seed_rooms[] = {
        {"101", "standard", "Standard room, 1 bed"},
        {"102", "standard", "Standard room, 2 beds"},
        {"103", "standard", "Standard room, 1 bed, garden view"},
        {"104", "standard", "Standard room, 2 beds, garden view"},
        {"201", "deluxe", "Deluxe room, king bed, sea view"},
        {"202", "deluxe", "Deluxe suite, 2 rooms, sea view"}
    };
    sqlite3_stmt *stmt = NULL;
    int count = 0;
    int rc;

    rc = sqlite3_prepare_v2(db, "SELECT COUNT(*) FROM rooms", -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        return -1;
    }
    rc = sqlite3_step(stmt);
    if (rc == SQLITE_ROW) {
        count = sqlite3_column_int(stmt, 0);
    }
    sqlite3_finalize(stmt);
    stmt = NULL;
    if (rc != SQLITE_ROW) {
        return -1;
    }
    if (count > 0) {
        return 0;
    }

    rc = sqlite3_prepare_v2(db,
                            "INSERT INTO rooms (room_number, room_type, description) "
                            "VALUES (?,?,?)",
                            -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        return -1;
    }

    for (size_t i = 0; i < sizeof(seed_rooms) / sizeof(seed_rooms[0]); i++) {
        sqlite3_reset(stmt);
        sqlite3_clear_bindings(stmt);
        sqlite3_bind_text(stmt, 1, seed_rooms[i].room_number, -1, SQLITE_STATIC);
        sqlite3_bind_text(stmt, 2, seed_rooms[i].room_type, -1, SQLITE_STATIC);
        sqlite3_bind_text(stmt, 3, seed_rooms[i].description, -1, SQLITE_STATIC);
        if (sqlite3_step(stmt) != SQLITE_DONE) {
            sqlite3_finalize(stmt);
            return -1;
        }
    }

    sqlite3_finalize(stmt);
    return 0;
}

int storage_init(const char *db_path) {
    char *err = NULL;
    int rc;

    pthread_mutex_lock(&db_lock);
    rc = sqlite3_open(db_path, &db);
    if (rc != SQLITE_OK) {
        pthread_mutex_unlock(&db_lock);
        return -1;
    }

    rc = sqlite3_exec(db, SCHEMA, NULL, NULL, &err);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Schema error: %s\n", err);
        sqlite3_free(err);
        pthread_mutex_unlock(&db_lock);
        return -1;
    }

    rc = storage_seed_rooms();
    pthread_mutex_unlock(&db_lock);
    return rc == 0 ? 0 : -1;
}

void booking_free_int_list(int *p) {
    free(p);
}

void storage_close(void) {
    pthread_mutex_lock(&db_lock);
    if (db != NULL) {
        sqlite3_close(db);
        db = NULL;
    }
    pthread_mutex_unlock(&db_lock);
}

int storage_room_list(Room **out, int *count) {
    sqlite3_stmt *stmt = NULL;
    Room *list = NULL;
    int capacity = 0;
    int n = 0;
    int rc;

    pthread_mutex_lock(&db_lock);
    rc = sqlite3_prepare_v2(db,
                            "SELECT room_id, room_number, room_type, description "
                            "FROM rooms ORDER BY room_id",
                            -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        pthread_mutex_unlock(&db_lock);
        return -1;
    }

    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        if (n == capacity) {
            int new_capacity = capacity == 0 ? 8 : capacity * 2;
            Room *new_list = realloc(list, (size_t)new_capacity * sizeof(Room));
            if (new_list == NULL) {
                free(list);
                sqlite3_finalize(stmt);
                pthread_mutex_unlock(&db_lock);
                return -1;
            }
            list = new_list;
            capacity = new_capacity;
        }

        memset(&list[n], 0, sizeof(Room));
        list[n].room_id = sqlite3_column_int(stmt, 0);
        copy_text(list[n].room_number, sizeof(list[n].room_number), sqlite3_column_text(stmt, 1));
        copy_text(list[n].room_type, sizeof(list[n].room_type), sqlite3_column_text(stmt, 2));
        copy_text(list[n].description, sizeof(list[n].description), sqlite3_column_text(stmt, 3));
        n++;
    }

    sqlite3_finalize(stmt);
    pthread_mutex_unlock(&db_lock);
    if (rc != SQLITE_DONE) {
        free(list);
        return -1;
    }

    *out = list;
    *count = n;
    return 0;
}

int storage_room_free_list(Room *list) {
    free(list);
    return 0;
}

int storage_conflict_check(int room_id, const char *check_in, const char *check_out) {
    sqlite3_stmt *stmt = NULL;
    int rc;
    int count = 0;

    pthread_mutex_lock(&db_lock);
    rc = sqlite3_prepare_v2(db,
                            "SELECT COUNT(*) FROM bookings "
                            "WHERE room_id=? AND status='active' "
                            "  AND check_in_date < ? "
                            "  AND check_out_date > ?",
                            -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        pthread_mutex_unlock(&db_lock);
        return -1;
    }

    sqlite3_bind_int(stmt, 1, room_id);
    sqlite3_bind_text(stmt, 2, check_out, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, check_in, -1, SQLITE_STATIC);

    rc = sqlite3_step(stmt);
    if (rc == SQLITE_ROW) {
        count = sqlite3_column_int(stmt, 0);
    }

    sqlite3_finalize(stmt);
    pthread_mutex_unlock(&db_lock);
    if (rc != SQLITE_ROW) {
        return -1;
    }

    return count > 0 ? 1 : 0;
}

int storage_availability(const char *check_in,
                         const char *check_out,
                         int **occupied_ids, int *count) {
    sqlite3_stmt *stmt = NULL;
    int *ids = NULL;
    int capacity = 0;
    int n = 0;
    int rc;

    pthread_mutex_lock(&db_lock);
    rc = sqlite3_prepare_v2(db,
                            "SELECT DISTINCT room_id FROM bookings "
                            "WHERE status='active' "
                            "  AND check_in_date < ? "
                            "  AND check_out_date > ?",
                            -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        pthread_mutex_unlock(&db_lock);
        return -1;
    }

    sqlite3_bind_text(stmt, 1, check_out, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, check_in, -1, SQLITE_STATIC);

    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        if (n == capacity) {
            int new_capacity = capacity == 0 ? 8 : capacity * 2;
            int *new_ids = realloc(ids, (size_t)new_capacity * sizeof(int));
            if (new_ids == NULL) {
                free(ids);
                sqlite3_finalize(stmt);
                pthread_mutex_unlock(&db_lock);
                return -1;
            }
            ids = new_ids;
            capacity = new_capacity;
        }
        ids[n++] = sqlite3_column_int(stmt, 0);
    }

    sqlite3_finalize(stmt);
    pthread_mutex_unlock(&db_lock);
    if (rc != SQLITE_DONE) {
        free(ids);
        return -1;
    }

    *occupied_ids = ids;
    *count = n;
    return 0;
}

int storage_booking_insert(const Booking *b) {
    sqlite3_stmt *stmt = NULL;
    int rc;
    int booking_id;

    pthread_mutex_lock(&db_lock);
    rc = sqlite3_prepare_v2(db,
                            "INSERT INTO bookings "
                            "(guest_name, email, check_in_date, check_out_date, "
                            " number_of_guests, room_id, created_at, status) "
                            "VALUES (?,?,?,?,?,?,?,?)",
                            -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        pthread_mutex_unlock(&db_lock);
        return -1;
    }

    sqlite3_bind_text(stmt, 1, b->guest_name, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 2, b->email, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 3, b->check_in_date, -1, SQLITE_STATIC);
    sqlite3_bind_text(stmt, 4, b->check_out_date, -1, SQLITE_STATIC);
    sqlite3_bind_int(stmt, 5, b->number_of_guests);
    sqlite3_bind_int(stmt, 6, b->room_id);
    sqlite3_bind_int64(stmt, 7, (sqlite3_int64)time(NULL));
    sqlite3_bind_text(stmt, 8, "active", -1, SQLITE_STATIC);

    rc = sqlite3_step(stmt);
    if (rc != SQLITE_DONE) {
        sqlite3_finalize(stmt);
        pthread_mutex_unlock(&db_lock);
        return -1;
    }

    booking_id = (int)sqlite3_last_insert_rowid(db);
    sqlite3_finalize(stmt);
    pthread_mutex_unlock(&db_lock);
    return booking_id;
}

int storage_booking_cancel(int booking_id) {
    sqlite3_stmt *stmt = NULL;
    int rc;
    int changes;

    pthread_mutex_lock(&db_lock);
    rc = sqlite3_prepare_v2(db,
                            "UPDATE bookings SET status='cancelled' WHERE booking_id=?",
                            -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        pthread_mutex_unlock(&db_lock);
        return -1;
    }

    sqlite3_bind_int(stmt, 1, booking_id);
    rc = sqlite3_step(stmt);
    changes = sqlite3_changes(db);
    sqlite3_finalize(stmt);
    pthread_mutex_unlock(&db_lock);

    if (rc != SQLITE_DONE || changes == 0) {
        return -1;
    }
    return 0;
}

int storage_booking_list(Booking **out, int *count) {
    sqlite3_stmt *stmt = NULL;
    Booking *list = NULL;
    int capacity = 0;
    int n = 0;
    int rc;

    pthread_mutex_lock(&db_lock);
    rc = sqlite3_prepare_v2(db,
                            "SELECT b.booking_id, b.guest_name, b.email, "
                            "       b.check_in_date, b.check_out_date, b.number_of_guests, "
                            "       b.room_id, r.room_number, r.room_type, "
                            "       b.created_at, b.status "
                            "FROM bookings b "
                            "JOIN rooms r ON r.room_id = b.room_id "
                            "WHERE b.status='active' "
                            "ORDER BY b.check_in_date",
                            -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        pthread_mutex_unlock(&db_lock);
        return -1;
    }

    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        if (n == capacity) {
            int new_capacity = capacity == 0 ? 8 : capacity * 2;
            Booking *new_list = realloc(list, (size_t)new_capacity * sizeof(Booking));
            if (new_list == NULL) {
                free(list);
                sqlite3_finalize(stmt);
                pthread_mutex_unlock(&db_lock);
                return -1;
            }
            list = new_list;
            capacity = new_capacity;
        }

        memset(&list[n], 0, sizeof(Booking));
        list[n].booking_id = sqlite3_column_int(stmt, 0);
        copy_text(list[n].guest_name, sizeof(list[n].guest_name), sqlite3_column_text(stmt, 1));
        copy_text(list[n].email, sizeof(list[n].email), sqlite3_column_text(stmt, 2));
        copy_text(list[n].check_in_date, sizeof(list[n].check_in_date), sqlite3_column_text(stmt, 3));
        copy_text(list[n].check_out_date, sizeof(list[n].check_out_date), sqlite3_column_text(stmt, 4));
        list[n].number_of_guests = sqlite3_column_int(stmt, 5);
        list[n].room_id = sqlite3_column_int(stmt, 6);
        copy_text(list[n].room_number, sizeof(list[n].room_number), sqlite3_column_text(stmt, 7));
        copy_text(list[n].room_type, sizeof(list[n].room_type), sqlite3_column_text(stmt, 8));
        list[n].created_at = sqlite3_column_int64(stmt, 9);
        copy_text(list[n].status, sizeof(list[n].status), sqlite3_column_text(stmt, 10));
        n++;
    }

    sqlite3_finalize(stmt);
    pthread_mutex_unlock(&db_lock);
    if (rc != SQLITE_DONE) {
        free(list);
        return -1;
    }

    *out = list;
    *count = n;
    return 0;
}
