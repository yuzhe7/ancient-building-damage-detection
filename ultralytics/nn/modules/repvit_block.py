import torch.nn as nn


class RepViTBlock(nn.Module):
    def __init__(self, c1, c2, kernel_size=3, stride=1, expansion_ratio=2):
        super().__init__()
        self.cv1 = nn.Conv2d(c1, c2, kernel_size, stride, padding=kernel_size // 2, groups=c1)
        self.act = nn.SiLU()
        hidden_dim = int(c2 * expansion_ratio)
        self.cv2 = nn.Conv2d(c2, hidden_dim, 1)
        self.cv3 = nn.Conv2d(hidden_dim, c2, 1)
        self.se = nn.Sequential(
            nn.AdaptiveAvgPool2d(1), nn.Conv2d(c2, c2 // 4, 1), nn.SiLU(), nn.Conv2d(c2 // 4, c2, 1), nn.Sigmoid()
        )

    def forward(self, x):
        identity = x
        x = self.act(self.cv1(x))
        x = self.act(self.cv2(x))
        x = self.cv3(x)
        x = x * self.se(x)
        return x + identity
