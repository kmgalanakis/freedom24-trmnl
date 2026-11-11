# Terminus extension

This folder holds the Terminus extension that turns the sidecar's JSON into a screen.
Both files use the format that Terminus itself exports and imports.

| File | Contents |
| --- | --- |
| `configuration.yml` | The extension settings and its exchange, which is the URL Terminus polls. |
| `template.html.liquid` | The Liquid template that renders the screen. |

## What the screen shows

- The portfolio total in `BASE_CURRENCY`.
- A 3×2 grid: change today, total profit or loss, invested amount, cost basis, cash, and the largest holding.
- An allocation bar with one segment for each holding of 0.5% or more.
- A table of up to 12 holdings, largest first. Holdings of 1% or more get two lines with name, quantity × price, and percentages. Smaller holdings get one compact line.

Negative values are bold and underlined. The "Today" and "Total P/L" cells turn black when they are negative.
If the sidecar returns an error, the screen shows the error text in place of the numbers.

## Set it up

You need a running sidecar first. See the main [README](../README.md).

1. Zip the two files. The zip must hold them at its top level, not inside a folder:

   ```bash
   cd terminus && zip ../extension.zip configuration.yml template.html.liquid
   ```

2. In Terminus, open **Extensions**, click **Upload**, and attach `extension.zip`. Terminus creates the extension and its exchange.
3. Open the new extension. Under **Exchanges**, open the exchange and replace `SIDECAR_HOST` with the LAN address of the machine that runs the sidecar.
   Do not use `localhost`. Terminus runs in its own container, so `localhost` points at Terminus itself.
4. Under **Build Matrix**, choose **Models** and select your device's model. The export format does not include this setting.
5. Save the extension, then click **Build**. Terminus renders a screen for each selected model.
6. Open your device's playlist and add the new screen.

To check the data before you build, open the extension and look at **Data**. It should show the sidecar's JSON under `source_1`.

## Settings

`configuration.yml` sets these values:

| Setting | Value | Meaning |
| --- | --- | --- |
| `kind` | `poll` | Terminus fetches the exchange URL on a schedule. |
| `interval`, `unit` | `15`, `minute` | Terminus polls every 15 minutes. |
| `mode` | `text` | Terminus renders the template as text, not as dithered art. |
| `exchanges[0].template` | `http://SIDECAR_HOST:8090/portfolio` | The sidecar's `/portfolio` endpoint. |

## Screen size

The layout was made for the model "Amazon Kindle PW 7th Gen (Custom)": 1072×1448 pixels, scale factor 1.6, rotation 0, 8-bit grayscale.
Terminus divides the size by the scale factor, so the template has about 670×905 CSS pixels to fill.

For another model, compute the same CSS size and compare.
If rows are cut off at the bottom, lower the font sizes in the `<style>` block or the `limit: 12` in the holdings loop.
If the screen looks empty, raise them.

## Keep the copies in sync

Terminus stores the live copy of the extension.
When you change the extension in Terminus, click its **Download** link on the **Extensions** page and unzip the export over these two files.

Before you commit, check two things:

- The export holds your real sidecar address in the exchange `template`. Replace it with `SIDECAR_HOST`.
- Terminus saves the template with Windows line endings. Convert them back to Unix line endings, so the diff shows only real changes:

  ```bash
  sed -i '' $'s/\r$//' template.html.liquid
  ```

  On Linux, drop the `''` after `-i`.
