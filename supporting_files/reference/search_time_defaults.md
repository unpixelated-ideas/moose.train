# Search Time Defaults and Transition Rules

This file documents the intended local-time behavior for the search form. All rules use U.S. East Coast civil time.

## Initial page load

The search date defaults to the current local date except for the 11:59 PM rollover case.

The search time defaults as follows:

- From 12:00 AM through 10:59 PM, use the next whole hour.
- From 11:00 PM through 11:44 PM, use 11:45 PM on the same date.
- From 11:45 PM through 11:58 PM, use the current time on the same date.
- At 11:59 PM, use 12:01 AM on the following date.

Examples:

- 3:23 PM on August 30 defaults to August 30 at 4:00 PM.
- 12:05 AM on August 30 defaults to August 30 at 1:00 AM.
- 11:10 PM on August 30 defaults to August 30 at 11:45 PM.
- 11:46 PM on August 30 defaults to August 30 at 11:46 PM.
- 11:59 PM on August 30 defaults to August 31 at 12:01 AM.

## Daylight-saving transition searches

When a user searches for a time inside a U.S. East Coast daylight-saving transition hour, the app moves the search to the next valid hour and shows a short status warning.

- Spring forward: on the second Sunday in March, 2:00 AM through 2:59 AM moves to 3:00 AM.
- Fall back: on the first Sunday in November, 1:00 AM through 1:59 AM moves to 2:00 AM to avoid the repeated ambiguous hour.

The adjustment happens only when a search is initiated. It does not persist in localStorage, cookies, or any backend store.
