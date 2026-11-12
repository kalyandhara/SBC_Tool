# Navigator "Add a birth chart": Match Enter Birthdata

Date: 2026-11-11. Requested via the session that started this one, relaying the user. Scope was chosen by the user: "Same look, Navigator fields".

## Goal

Make the Navigator tab's "Add a birth chart" form look and behave like Executive Overview's "Enter Birthdata" form, so a saved birth profile can feed a Navigator chart directly. Keep the Navigator's required fields and validation.

## Form

Same layout, classes and controls as `#birth-data-form` in `templates/index.html`, with ids prefixed `nav-bd-` so they are unique:

- **Birthdate (Gregorian):** the same date picker wrap.
- **Birthtime (0–24 hrs):** the same time input with `step="1"`.
- **City name:** Search Worldwide and Search USA buttons, a status line, and a results list.
- **Longitude and Latitude:** degree, minute and second fields.
- **Time Zone (Standard Time):** hours and minutes, the same inputs as Executive Overview.
- **IANA timezone (Navigator only):** a text field, filled automatically from the chosen city result's timezone, otherwise from `GET /api/tz/from_coords` using the coordinates. Editable, and validated by the server. Labelled "Time zone name (handles daylight saving)".
- **Label:** optional, as now.
- **Saved profile:** a select listing Executive Overview profiles from `GET /api/astro/profile?user_key=default`, with a "Load Selected Profile" button and a "Load Latest Profile" button. Loading fills the form from the profile's data:
    - date and time;
    - city;
    - lat and lon `{deg, min, sec}`;
    - tz hours and minutes;
    - the IANA timezone, derived from the coordinates.
- **Not on this form:** gender, altitude, pressure and temperature are left out, because the Navigator score does not use them. Rename, Set Default, Delete, Export and Import also stay on Executive Overview. A short note links there.
- **Submit:** a "Create Navigator chart" button sends JSON `{label, birth_date, birth_time, tz (IANA), lat, lon}` to `POST /api/navigator/profile`, as now.
    - Decimal lat and lon come from degrees, minutes and seconds. The sign comes from the degree field, and a negative zero degree is handled with a hemisphere sign kept from the source value.
    - Seconds on the time are kept.
    - Errors show the server's fixed message.

## Shared code

- **City search:** refactor `static/js/birth-city.js` into a reusable initializer, for example `window.initBirthCity({cityInput, status, list, lonDeg, …, onSelect})`. Executive Overview calls it with its current ids, and its behaviour must not change. The Navigator calls it with `nav-bd-` ids, and `onSelect` receives the city's timezone.
- **Pickers:** reuse the existing date and time picker behaviour (`data-picker-for`) if it is generic. Otherwise call it with the new ids.

## Rules

- `textContent` only for server strings. No birth data in URLs, `localStorage` or logs. The existing Executive Overview code that uses localStorage is not touched and not copied.
- The Navigator's validation is unchanged: the server still rejects bad input.
- No new CDN. Works at 375px with no sideways scroll, in both themes.
- Page tests check the new markup and labels, and can fail. Executive Overview's existing tests keep passing.
- Verified in the running app with no console errors:
    - search a city, fill the coordinates and timezone, and create a chart;
    - load a saved profile and create a chart;
    - Executive Overview's form still searches and fills.
