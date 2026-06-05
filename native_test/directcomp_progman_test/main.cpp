#include <windows.h>
#include <d3d11.h>
#include <dxgi.h>
#include <dcomp.h>
#include <wrl/client.h>
#include <iostream>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")
#pragma comment(lib, "dcomp.lib")

using Microsoft::WRL::ComPtr;

static bool KeyDown(int vk)
{
    return (GetAsyncKeyState(vk) & 0x8000) != 0;
}

static bool ShouldQuit()
{
    // Esc / F12 / Ctrl + Alt + Q
    return KeyDown(VK_ESCAPE)
        || KeyDown(VK_F12)
        || (KeyDown(VK_CONTROL) && KeyDown(VK_MENU) && KeyDown('Q'));
}

static HWND FindProgman()
{
    return FindWindowW(L"Progman", nullptr);
}

int main()
{
    std::cout << "[INFO] DirectComposition Progman test\n";
    std::cout << "[INFO] Quit: Esc / F12 / Ctrl + Alt + Q\n";
    std::cout << "[INFO] Auto closes after 30 seconds\n";

    HWND progman = FindProgman();

    if (!progman)
    {
        std::cout << "[ERROR] Progman not found.\n";
        return 1;
    }

    std::cout << "[INFO] Progman HWND: " << progman << "\n";

    RECT rc{};
    GetWindowRect(progman, &rc);

    int width = rc.right - rc.left;
    int height = rc.bottom - rc.top;

    std::cout << "[INFO] Progman size: " << width << " x " << height << "\n";

    HRESULT hr = S_OK;

    ComPtr<ID3D11Device> d3dDevice;
    ComPtr<ID3D11DeviceContext> d3dContext;
    D3D_FEATURE_LEVEL featureLevel{};

    hr = D3D11CreateDevice(
        nullptr,
        D3D_DRIVER_TYPE_HARDWARE,
        nullptr,
        D3D11_CREATE_DEVICE_BGRA_SUPPORT,
        nullptr,
        0,
        D3D11_SDK_VERSION,
        &d3dDevice,
        &featureLevel,
        &d3dContext
    );

    if (FAILED(hr))
    {
        std::cout << "[ERROR] D3D11CreateDevice failed. HRESULT=0x"
                  << std::hex << hr << "\n";
        return 1;
    }

    std::cout << "[INFO] D3D11 device created.\n";

    ComPtr<IDXGIDevice> dxgiDevice;
    hr = d3dDevice.As(&dxgiDevice);

    if (FAILED(hr))
    {
        std::cout << "[ERROR] Query IDXGIDevice failed. HRESULT=0x"
                  << std::hex << hr << "\n";
        return 1;
    }

    ComPtr<IDCompositionDevice> dcompDevice;

    hr = DCompositionCreateDevice(
        dxgiDevice.Get(),
        __uuidof(IDCompositionDevice),
        reinterpret_cast<void**>(dcompDevice.GetAddressOf())
    );

    if (FAILED(hr))
    {
        std::cout << "[ERROR] DCompositionCreateDevice failed. HRESULT=0x"
                  << std::hex << hr << "\n";
        return 1;
    }

    std::cout << "[INFO] DirectComposition device created.\n";

    ComPtr<IDCompositionTarget> target;

    // IMPORTANT:
    // topmost = FALSE means visual tree should be behind children of Progman.
    hr = dcompDevice->CreateTargetForHwnd(
        progman,
        FALSE,
        target.GetAddressOf()
    );

    if (FAILED(hr))
    {
        std::cout << "[ERROR] CreateTargetForHwnd failed. HRESULT=0x"
                  << std::hex << hr << "\n";
        return 1;
    }

    std::cout << "[INFO] DirectComposition target created for Progman.\n";

    ComPtr<IDCompositionVisual> visual;
    hr = dcompDevice->CreateVisual(visual.GetAddressOf());

    if (FAILED(hr))
    {
        std::cout << "[ERROR] CreateVisual failed. HRESULT=0x"
                  << std::hex << hr << "\n";
        return 1;
    }

    ComPtr<IDCompositionSurface> surface;

    hr = dcompDevice->CreateSurface(
        width,
        height,
        DXGI_FORMAT_B8G8R8A8_UNORM,
        DXGI_ALPHA_MODE_IGNORE,
        surface.GetAddressOf()
    );

    if (FAILED(hr))
    {
        std::cout << "[ERROR] CreateSurface failed. HRESULT=0x"
                  << std::hex << hr << "\n";
        return 1;
    }

    POINT offset{};
    ComPtr<ID3D11Texture2D> texture;

    hr = surface->BeginDraw(
        nullptr,
        __uuidof(ID3D11Texture2D),
        reinterpret_cast<void**>(texture.GetAddressOf()),
        &offset
    );

    if (FAILED(hr))
    {
        std::cout << "[ERROR] Surface BeginDraw failed. HRESULT=0x"
                  << std::hex << hr << "\n";
        return 1;
    }

    ComPtr<IDXGISurface> dxgiSurface;
    hr = texture.As(&dxgiSurface);

    if (FAILED(hr))
    {
        std::cout << "[ERROR] Texture to IDXGISurface failed. HRESULT=0x"
                  << std::hex << hr << "\n";
        return 1;
    }

    DXGI_MAPPED_RECT mapped{};
    hr = dxgiSurface->Map(&mapped, DXGI_MAP_WRITE);

    if (FAILED(hr))
    {
        std::cout << "[ERROR] DXGI surface map failed. HRESULT=0x"
                  << std::hex << hr << "\n";
        return 1;
    }

    // Fill with blue/purple-ish background.
    for (int y = 0; y < height; y++)
    {
        unsigned char* row = mapped.pBits + y * mapped.Pitch;

        for (int x = 0; x < width; x++)
        {
            int i = x * 4;

            row[i + 0] = 90;   // B
            row[i + 1] = 35;   // G
            row[i + 2] = 20;   // R
            row[i + 3] = 255;  // A
        }
    }

    dxgiSurface->Unmap();

    hr = surface->EndDraw();

    if (FAILED(hr))
    {
        std::cout << "[ERROR] Surface EndDraw failed. HRESULT=0x"
                  << std::hex << hr << "\n";
        return 1;
    }

    visual->SetContent(surface.Get());
    target->SetRoot(visual.Get());

    hr = dcompDevice->Commit();

    if (FAILED(hr))
    {
        std::cout << "[ERROR] DirectComposition Commit failed. HRESULT=0x"
                  << std::hex << hr << "\n";
        return 1;
    }

    std::cout << "[INFO] DirectComposition committed.\n";
    std::cout << "[INFO] Check desktop now:\n";
    std::cout << "       1. Is blue/purple background visible?\n";
    std::cout << "       2. Are desktop icons visible above it?\n";
    std::cout << "       3. Does right-click work?\n";

    DWORD start = GetTickCount();

    while (GetTickCount() - start < 30000)
    {
        if (ShouldQuit())
        {
            std::cout << "[INFO] Manual quit requested.\n";
            break;
        }

        Sleep(20);
    }

    target->SetRoot(nullptr);
    dcompDevice->Commit();

    std::cout << "[INFO] Test closed.\n";
    return 0;
}