#pragma once
#include <stdint.h>

typedef struct {
    int  room_id;
    char room_number[8];
    char room_type[16];
    char description[128];
} Room;

typedef struct {
    int     booking_id;
    char    guest_name[64];
    char    email[64];
    char    check_in_date[12];
    char    check_out_date[12];
    int     number_of_guests;
    int     room_id;
    char    room_number[8];
    char    room_type[16];
    int64_t created_at;
    char    status[16];
} Booking;

int  booking_create(const Booking *b);
int  booking_cancel(int booking_id);
int  booking_list(Booking **out, int *count);
void booking_free_list(Booking *list);
int  booking_check_conflict(int room_id, const char *check_in, const char *check_out);
