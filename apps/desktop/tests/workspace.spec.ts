import { test, expect, type Page } from "@playwright/test";

async function connect(page: Page) {
  await page.goto("/");
  await page.getByLabel("Địa chỉ engine").fill("http://127.0.0.1:8766");
  await page
    .getByLabel("Session token", { exact: true })
    .fill("e2e-isolated-test-session-token");
  await page.getByRole("button", { name: "Kết nối workspace" }).click();
  await expect(page.getByText("Cơ hội tốt bắt đầu")).toBeVisible();
}

test("real import → analysis → customer → opportunity → care → backup", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await connect(page);
  await page
    .getByRole("button", { name: "Khám phá lead", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "Nhập JSON", exact: true }).click();
  await page.getByLabel("Nội dung JSON").fill(
    JSON.stringify({
      platform: "FACEBOOK",
      posts: [
        {
          platform: "FACEBOOK",
          external_id: "e2e-buyer",
          author_id: "e2e-author",
          author_name: "Khách E2E",
          url: "https://www.facebook.com/posts/example",
          content:
            "Nhà mình 3 tầng cần lắp wifi và camera gấp hôm nay. 0989626638",
          posted_at: new Date().toISOString(),
        },
      ],
    }),
  );
  await page.getByRole("button", { name: "Nhập & phân tích" }).click();
  await expect(page.getByText("Khách E2E", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Xem phân tích" }).click();
  await expect(page.getByText("CALL_NOW", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Lưu vào khách hàng 360" }).click();
  await expect(page.getByRole("heading", { name: "Hồ sơ 360" })).toBeVisible();
  await page.getByLabel("Cơ hội ban đầu (tùy chọn)").fill("Combo E2E");
  await page.getByLabel("Giá trị dự kiến (VND)").fill("3000000");
  await page.getByRole("button", { name: "Chuyển thành khách hàng" }).click();
  await expect(page.getByText("Khách hàng CRM", { exact: true })).toBeVisible();
  await page
    .getByPlaceholder("Thông tin cần nhớ về khách hàng…")
    .fill("Cần kiểm tra hạ tầng trước khi lắp");
  await page.getByRole("button", { name: "Lưu ghi chú" }).click();
  await expect(
    page.getByText("Cần kiểm tra hạ tầng trước khi lắp", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Cơ hội bán hàng", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: "Combo E2E" })).toBeVisible();
  await page.getByLabel("Giai đoạn Combo E2E").selectOption("QUOTED");
  await expect(
    page
      .locator(".stage-quoted")
      .locator("..")
      .locator("..")
      .getByRole("heading", { name: "Combo E2E" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Lịch chăm sóc", exact: true })
    .click();
  await page.getByRole("button", { name: "Tạo lịch chăm sóc" }).click();
  const modal = page.getByRole("dialog");
  await modal
    .getByLabel("Khách hàng", { exact: true })
    .selectOption({ label: "Khách E2E" });
  await modal.getByLabel("Việc cần làm").fill("Gọi lại E2E");
  await modal.getByLabel("Thời gian trên máy của bạn").fill("2026-10-01T09:00");
  await modal.getByRole("button", { name: "Lưu lịch chăm sóc" }).click();
  await expect(
    page.getByRole("heading", { name: "Gọi lại E2E" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Hoàn thành", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Gọi lại E2E" })).toHaveCount(
    0,
  );
  await page
    .getByRole("button", { name: "Cài đặt & dữ liệu", exact: true })
    .click();
  await page.getByRole("button", { name: "Tạo bản sao lưu" }).click();
  await expect(page.locator(".backup-row")).toHaveCount(1);
  await page.getByRole("button", { name: "Tổng quan", exact: true }).click();
  await expect(page.locator(".metrics")).toBeVisible();
  await page.screenshot({
    path: "test-results/workspace-overview.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("connection rejects wrong token and mobile layout stays usable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByLabel("Địa chỉ engine").fill("http://127.0.0.1:8766");
  await page.getByLabel("Session token", { exact: true }).fill("wrong");
  await page.getByRole("button", { name: "Kết nối workspace" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Invalid internal session token",
  );
  await page
    .getByLabel("Session token", { exact: true })
    .fill("e2e-isolated-test-session-token");
  await page.getByRole("button", { name: "Kết nối workspace" }).click();
  await expect(page.getByText("Cơ hội tốt bắt đầu")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("button", { name: "Khách hàng 360", exact: true })
    .click();
  await page.getByRole("button", { name: "Thêm liên hệ" }).click();
  await page.getByLabel("Họ tên").fill("Liên hệ Mobile");
  await page.getByRole("button", { name: "Tạo liên hệ", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Liên hệ Mobile" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/workspace-mobile.png",
    fullPage: true,
  });
});

test("source failure is actionable and blacklist persists", async ({
  page,
}) => {
  await connect(page);
  await page.getByRole("button", { name: "Bộ lọc & blacklist" }).click();
  await page.getByLabel("Giá trị", { exact: true }).fill("cho vay");
  await page.getByLabel("Lý do", { exact: true }).fill("Không phù hợp");
  await page.getByRole("button", { name: "Lưu quy tắc" }).click();
  await expect(page.getByText("cho vay", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Khám phá lead", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "Tạo lượt quét" }).click();
  await page.getByLabel("Nguồn", { exact: true }).selectOption("THREADS");
  await page.getByLabel("Từ khóa (cách nhau bằng dấu phẩy)").fill("wifi");
  await page.getByRole("button", { name: "Bắt đầu quét" }).click();
  await expect(
    page.locator(".job").filter({ hasText: "Threads" }),
  ).toContainText("chưa cấu hình access token");
});
