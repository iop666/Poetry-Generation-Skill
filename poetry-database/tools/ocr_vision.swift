// ocr_vision.swift —— 用 macOS Vision 框架离线识别中文书页
//
// 为什么不用 PaddleOCR-VL：
//   本轮环境内没有可用的 PaddleOCR-VL 端点（内置 VLM 代理对多种请求体均返回 401/400），
//   而 macOS 自带 Vision 的 VNRecognizeTextRequest 支持简繁中文、完全离线、零 token。
//   本工具产出会明确标注识别引擎为 "macos-vision"，不得冒充 PaddleOCR 结果。
//
// 用法：
//   ./ocr_vision <图片路径> [<图片路径> ...]
// 输出：每个文件输出一个 JSON 行 {"file":..., "lines":[...], "conf":均值}
import Foundation
import Vision
import AppKit

func ocr(_ path: String) -> (lines: [String], conf: Double) {
    guard let img = NSImage(contentsOfFile: path),
          let tiff = img.tiffRepresentation,
          let bmp = NSBitmapImageRep(data: tiff),
          let cg = bmp.cgImage else {
        return ([], 0)
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    // 语言纠正必须关：开启后会把「平」强行纠成常用字，正文用字被改写。
    request.usesLanguageCorrection = false
    request.recognitionLanguages = ["zh-Hans", "zh-Hant"]
    // 必须用 rev2。实测 rev3 把「平」识成「瓜」、「仄」识成「厂」
    // （一页 9 处「瓜」），而格律书里这两个字是规则本体，错一个就毁一条规则。
    // rev2 在同类书页上「平对仄」正确、零「瓜」，置信 0.93。rev1 直接乱码。
    request.revision = 2
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    do { try handler.perform([request]) } catch { return ([], 0) }

    guard let obs = request.results else { return ([], 0) }
    var lines: [String] = []
    var sum = 0.0
    for o in obs {
        guard let top = o.topCandidates(1).first else { continue }
        lines.append(top.string)
        sum += Double(top.confidence)
    }
    return (lines, obs.isEmpty ? 0 : sum / Double(obs.count))
}

let args = Array(CommandLine.arguments.dropFirst())
for p in args {
    let (lines, conf) = ocr(p)
    let obj: [String: Any] = ["file": p, "lines": lines, "conf": conf, "n": lines.count]
    if let d = try? JSONSerialization.data(withJSONObject: obj, options: []),
       let s = String(data: d, encoding: .utf8) {
        print(s)
    }
}
