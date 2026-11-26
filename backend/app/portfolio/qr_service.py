"""
PortfolioAI - Public Portfolio QR Code Generation Service
Creates high-contrast, ATS-friendly PNG QR codes pointing exclusively
to the published public URL of a portfolio.
"""

import io
import re
import qrcode
from qrcode.constants import ERROR_CORRECT_M


class QRCodeError(Exception):
    """Base exception for QR code generation failures."""
    pass


class PortfolioUnpublishedError(QRCodeError):
    """Raised when attempting to generate a public QR code for an unpublished portfolio."""
    pass


class PortfolioQRService:
    """Encapsulates QR code image generation for published public portfolios."""

    @classmethod
    def generate_qr_png(cls, portfolio, box_size: int = 10, border: int = 3) -> io.BytesIO:
        """
        Generate a PNG QR code for the portfolio's public URL.

        Raises:
            PortfolioUnpublishedError: If the portfolio is not published.
            QRCodeError: If QR code image synthesis fails.
        """
        if not portfolio.is_published:
            raise PortfolioUnpublishedError(
                f"Portfolio '{portfolio.title}' is currently a private draft. "
                "Publish your portfolio first to generate a public QR code."
            )

        public_url = portfolio.get_public_url()
        if not public_url:
            raise QRCodeError("Could not resolve a valid public URL for this portfolio.")

        # Validate accent color if user wants styled QR code or standard black
        fill_color = "black"
        if portfolio.accent_color and re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", portfolio.accent_color):
            # We can use a dark tinted color or high-contrast dark navy for reliable mobile scanning
            fill_color = "#0f172a"

        try:
            qr = qrcode.QRCode(
                version=None,
                error_correction=ERROR_CORRECT_M,
                box_size=max(4, min(20, box_size)),
                border=max(1, min(6, border)),
            )
            qr.add_data(public_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color=fill_color, back_color="white")

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            return buffer
        except PortfolioUnpublishedError:
            raise
        except Exception as e:
            raise QRCodeError(f"Failed to generate QR code image: {str(e)}")
