import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime


def create_activity_chart_pro(daily_stats: dict):
    sorted_items = sorted(
        daily_stats.items(),
        key=lambda x: datetime.strptime(x[0], "%d/%m/%Y")
    )

    dates = [x[0] for x in sorted_items]
    hours = [x[1]["seconds"] / 3600 for x in sorted_items]

    plt.style.use("dark_background")
    plt.figure(figsize=(10, 5))

    plt.plot(dates, hours, marker='o')
    plt.fill_between(dates, hours, alpha=0.2)

    plt.xticks(rotation=45)
    plt.ylabel("Hours")
    plt.title("Activity Chart")

    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close()

    return buffer