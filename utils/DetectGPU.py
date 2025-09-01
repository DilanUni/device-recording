import winreg
from typing import Optional, Final

class DetectGPU:
    """
    Utility class to detect GPU vendor (NVIDIA or AMD) on Windows systems.
    Falls back to CPU if no dedicated GPU is detected.
    """
    
    NVIDIA_REG_PATH: Final[str] = r"SOFTWARE\NVIDIA Corporation\Global\NvControlPanel2"
    AMD_REG_PATH: Final[str] = r"SOFTWARE\AMD"
    
    @staticmethod
    def detect_gpu_vendor() -> str:
        """
        Detects the GPU vendor by checking Windows registry keys.
        
        Returns:
            str: 'nvidia', 'amd', or 'cpu' if no dedicated GPU is detected.
        """
        try:
            # Check for NVIDIA registry key
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, DetectGPU.NVIDIA_REG_PATH):
                return "nvidia"
        except FileNotFoundError:
            print("NVIDIA not found, continue to check AMD")
            pass
        except Exception as e:
            print("Log registry access error if needed")
            pass
        
        try:
            # Check for AMD registry key
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, DetectGPU.AMD_REG_PATH):
                return "amd"
        except FileNotFoundError:
            print("AMD not found, fall back to CPU")
            pass
        except Exception as e:
            print("Log registry access error if needed")
            pass
        
        print("No dedicated GPU detected")
        return "cpu"
    
    @staticmethod
    def get_optimal_codec(vendor: Optional[str] = None) -> str:
        """
        Returns the optimal FFmpeg codec based on the detected hardware.
        
        Args:
            vendor: GPU vendor string. If None, auto-detects the vendor.
            
        Returns:
            str: FFmpeg codec string optimized for the detected hardware.
        """
        if vendor is None:
            vendor = DetectGPU.detect_gpu_vendor()
        
        # Codec mapping based on hardware capabilities
        codec_map: Final[dict[str, str]] = {
            "nvidia": "hevc_nvenc",    # H.265 NVIDIA NVENC encoder (most efficient for NVIDIA)
            "amd": "hevc_amf",         # H.265 AMD AMF encoder (best for AMD GPUs)
            "cpu": "libx265"           # H.265 software encoder (best for CPU encoding)
        }
        
        return codec_map.get(vendor, "libx265")  # Default to CPU codec if vendor unknown

if __name__ == "__main__":
    gpu_vendor = DetectGPU.detect_gpu_vendor()
    print(f"Detected hardware: {gpu_vendor}")
    
    optimal_codec = DetectGPU.get_optimal_codec()
    print(f"Optimal codec: {optimal_codec}")
    
    nvidia_codec = DetectGPU.get_optimal_codec("nvidia")
    amd_codec = DetectGPU.get_optimal_codec("amd")
    cpu_codec = DetectGPU.get_optimal_codec("cpu")
    
    print(f"NVIDIA codec: {nvidia_codec}")
    print(f"AMD codec: {amd_codec}")
    print(f"CPU codec: {cpu_codec}")