# FCPXML 1.13 Rules for Resolve Import

This document enumerates the main rules and quirks for generating valid FCPXML 1.13 for DaVinci Resolve.

## Key Rules

- **Frame Duration**: All durations and offsets must use the canonical project rate. FCPXML uses `frameDuration` (e.g., "1001/24000s" for 23.976 fps).
- **Timeline tcStart**: Map the timeline's `tcStart` to the `start` attribute on the `sequence`.
- **Drop-Frame/Non-Drop-Frame**: Set `format`'s `frameDuration` and include `tcFormat="DF"` for drop-frame rates (29.97, 59.94, etc).
- **Assets**: Each unique source file must be declared as an `<asset>` with the correct path, format, and rate.
- **Spine Rules**: All primary timeline events must be placed in the `<spine>`, transitions are represented as adjacent `<transition>` elements.

## Minimal Example FCPXML Skeleton

```xml
<fcpxml version="1.13">
  <resources>
    <format id="r1" name="FFVideoFormat1080p24" frameDuration="1/24s" width="1920" height="1080"/>
    <asset id="src1" name="V1_Clip.mov" start="0s" duration="100/24s" hasVideo="1" format="r1" src="/media/V1_Clip.mov"/>
  </resources>
  <library>
    <event name="AAF Import">
      <project name="AAF Timeline">
        <sequence format="r1" tcStart="0s" duration="150/24s">
          <spine>
            <clip name="V1_Clip.mov" duration="100/24s" start="0s" offset="0s" ref="src1"/>
            <transition name="Dissolve" duration="50/24s"/>
            <clip name="V2_Clip.mov" duration="50/24s" start="0s" offset="100/24s" ref="src2"/>
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
```

## References

- [FCPXML 1.13 Apple Docs](https://developer.apple.com/documentation/professional_video_applications/fcpxml_reference)
- [Resolve FCPXML Import Quirks](https://forum.blackmagicdesign.com/)
