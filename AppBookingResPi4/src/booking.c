#include "booking.h"
#include "storage.h"
#include <stdlib.h>

int booking_create(const Booking *b) {
    if (storage_conflict_check(b->room_id, b->check_in_date, b->check_out_date) == 1)
        return -2;
    return storage_booking_insert(b);
}

int booking_cancel(int booking_id) {
    return storage_booking_cancel(booking_id);
}

int booking_list(Booking **out, int *count) {
    return storage_booking_list(out, count);
}

void booking_free_list(Booking *list) {
    free(list);
}

int booking_check_conflict(int room_id, const char *check_in, const char *check_out) {
    return storage_conflict_check(room_id, check_in, check_out);
}
