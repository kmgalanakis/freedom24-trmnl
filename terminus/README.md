# Terminus extension

This folder holds the Terminus extension that turns the sidecar's JSON into a screen.

| File | Contents |
| --- | --- |
| `template.liquid` | The Liquid template. Paste it into the extension's **Template and Input** field. |
| `extension.json` | The extension settings, the exchange (the URL Terminus polls), and the screen model the layout was made for. |

The extension and the exchange are separate objects in Terminus. `extension.json` keeps them apart for that reason.

## What the screen shows

- The portfolio total in `BASE_CURRENCY`.
- A 3×2 grid: change today, total profit or loss, invested amount, cost basis, cash, and the largest holding.
- An allocation bar with one segment for each holding of 0.5% or more.
- A table of up to 12 holdings, largest first. Holdings of 1% or more get two lines with name, quantity × price, and percentages. Smaller holdings get one compact line.

Negative values are bold and underlined. The "Today" and "Total P/L" cells turn black when they are negative.
If the sidecar returns an error, the screen shows the error text in place of the numbers.

## Set it up

You need a running sidecar first. See the main [README](../README.md).

1. In Terminus, open **Extensions** and create a new extension.
2. Copy the values from the `extension` object in `extension.json`: label, name, description, kind **Poll**, mode **Text**, interval **15**, unit **Minute**.
3. Under **Exchanges**, add an exchange with verb **GET** and the URL `http://SIDECAR_HOST:8090/portfolio`.
   Replace `SIDECAR_HOST` with the LAN address of the machine that runs the sidecar.
4. Paste `template.liquid` into **Template and Input**.
5. Under **Build Matrix**, choose **Models** and select your device's model.
6. Save the extension, then click **Build**. Terminus renders a screen for each selected model.
7. Open your device's playlist and add the new screen.

To check the data before you build, open the extension and look at **Data**. It should show the sidecar's JSON under `source_1`.

Terminus also has an [Extensions API](https://github.com/usetrmnl/terminus/blob/main/doc/api.adoc#extensions) for scripted setup.
The `extension` object in `extension.json` matches the API's request body, and the template goes in its `template` field.

## Screen size

The layout fits a model of 1072×1448 pixels with a scale factor of 1.6.
Terminus divides the size by the scale factor, so the template has about 670×905 CSS pixels to fill.

For another model, compute the same CSS size and compare.
If rows are cut off at the bottom, lower the font sizes in the `<style>` block or the `limit: 12` in the holdings loop.
If the screen looks empty, raise them.

## Keep the copies in sync

Terminus stores its own copy of the template.
After you edit it in Terminus, copy it back into `template.liquid` and commit it.
