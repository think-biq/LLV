# LLV

LLV enables you to record and play back [live link](https://docs.unrealengine.com/en-US/Engine/Animation/LiveLinkPlugin/index.html) frames, sent by [Epic Games](https://www.epicgames.com)' [ARKit](https://developer.apple.com/augmented-reality/arkit/) face capture [iOS app](https://apps.apple.com/us/app/live-link-face/id1495370836).

## Issues and discussion

Checkout [the wiki](https://github.com/think-biq/LLV/wiki) for more information on creating issues.

## Quick start

Checkout [this video](https://www.youtube.com/watch?v=RTwibwX4U_s), on how to setup LLV to be used with the MetaHuman example project.
[![](https://img.youtube.com/vi/RTwibwX4U_s/0.jpg)](http://www.youtube.com/watch?v=RTwibwX4U_s "Click to play on Youtube.com")

## Usage

### Create or use recordings

#### Record

Listens for 256 incoming frames on all interfaces and standard port *11111* and writes the recording to a file named *dao.gesichter*.

```bash
python llv.py record --frames 256 --output dao.gesichter
```

#### Replay

Play one of the example recordings and send it to a host machine at *10.0.0.69* with implicit standard port of *11111* and 60 frames per seconds.

```bash
python llv.py play --host 10.0.0.69 examples/dao.gesichter
```

### Inspecting or changing recordings

Recordings are stored as lines of base64 encoded frames. You can unpack recording files, to create a cleartext version, letting you inspect the frames as a json array.
If you'd like to create your own frames by hand or script, you can pack it for the use with LLV.

#### Unpacking

```bash
python llv.py unpack examples/dao.gesichter dao.klare-gesichter
```

#### Packing

```bash
python llv.py pack dao.klare-gesichter dao.gesichter
```

## Anatomy

### Frame layout

The packet sizes of a frame are defined in the [engine code](https://github.com/EpicGames/UnrealEngine/blob/2bf1a5b83a7076a0fd275887b373f8ec9e99d431/Engine/Plugins/Runtime/AR/AppleAR/AppleARKitFaceSupport/Source/AppleARKitFaceSupport/Private/AppleARKitLiveLinkSource.cpp#L256) as:

```c++
//                                         PacketVersion                    FrameTime                     BlendShapeCount Blendshapes                                        SubjectName             DeviceID
const uint32 MAX_BLEND_SHAPE_PACKET_SIZE = sizeof(BLEND_SHAPE_PACKET_VER) + sizeof(FQualifiedFrameTime) + sizeof(uint8) + (sizeof(float) * (uint64)EARFaceBlendShape::MAX) + (sizeof(TCHAR) * 256) + (sizeof(TCHAR) * 256);
const uint32 MIN_BLEND_SHAPE_PACKET_SIZE = sizeof(BLEND_SHAPE_PACKET_VER) + sizeof(FQualifiedFrameTime) + sizeof(uint8) + (sizeof(float) * (uint64)EARFaceBlendShape::MAX) +  sizeof(TCHAR)        +  sizeof(TCHAR);

```

This results in the minimum frame size being 264 bytes and the maximum being 774 bytes.

The layout is defined as:

* PacketVersion ->  1 byte  (uint8_t)
* FrameTime -> 16 bytes (int32 + float + int32 + int32)
* BlendShapeCount -> 1 byte (uint8_t)
* List of blenshape values -> Blendshape Count * 4 bytes (float)
* Subject Name -> Name Length * 1 byte (char)
* Device ID -> ID Length * 1 byte (char)

There are a maximum of 61 blendshapes supported. See the apple [ARKit docs](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation) for more info.
