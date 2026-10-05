import {
  useEffect,
  useState,
  useId,
  useRef,
  cloneElement,
  isValidElement,
  type ReactElement,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  Activity,
  ArrowRight,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronRight,
  Download,
  FileJson,
  LayoutDashboard,
  Loader2,
  MessageCircle,
  Plus,
  Search,
  Settings,
  Shield,
  Users,
  Radar,
  X,
  Target,
  Database,
  RefreshCw,
  Bookmark,
  ExternalLink,
  Wifi,
  Send,
} from "lucide-react";
import {
  configure,
  desktopConnection,
  exportCustomers,
  liveFeed,
  request,
  openSource,
  sourceUrl,
  type Connection,
} from "./api";
import {
  labels,
  stages,
  type Post,
  type Person,
  type Profile,
  type Customer,
  type Customer360,
  type Task,
  type Job,
  type Analysis,
  type Comment,
  type Rule,
  type Conversation,
  type Message,
} from "./types";

type Page =
  | "overview"
  | "leads"
  | "contacts"
  | "pipeline"
  | "care"
  | "zalo"
  | "campaigns"
  | "blacklist"
  | "settings";
type Act = (work: () => Promise<unknown>, message?: string) => Promise<void>;
const nav = [
  { id: "overview", title: "Tổng quan", icon: LayoutDashboard },
  { id: "leads", title: "Khám phá lead", icon: Radar },
  { id: "contacts", title: "Khách hàng 360", icon: Users },
  { id: "pipeline", title: "Cơ hội bán hàng", icon: Target },
  { id: "care", title: "Lịch chăm sóc", icon: CalendarDays },
  { id: "zalo", title: "Trợ lý Zalo", icon: MessageCircle },
  { id: "campaigns", title: "Chăm sóc OA", icon: Send },
  { id: "blacklist", title: "Bộ lọc & blacklist", icon: Shield },
  { id: "settings", title: "Cài đặt & dữ liệu", icon: Settings },
] as const;

function useData<T>(path: string | null, version: number) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false);
  useEffect(() => {
    setData(null);
  }, [path]);
  useEffect(() => {
    let active = true;
    setError("");
    setLoading(true);
    if (!path) {
      setData(null);
      setLoading(false);
      return;
    }
    request<T>(path)
      .then((result) => {
        if (active) setData(result);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [path, version]);
  return { data, error, loading };
}
const date = (value: string | null) =>
  value
    ? new Date(
        value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value)
          ? value
          : `${value}Z`,
      ).toLocaleString("vi-VN", {
        timeZone: "Asia/Ho_Chi_Minh",
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";
const money = (value: number) =>
  new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
const value = (form: HTMLFormElement, key: string) =>
  String(new FormData(form).get(key) || "");
const initials = (name: string) =>
  name
    .split(" ")
    .filter(Boolean)
    .slice(-2)
    .map((x) => x[0])
    .join("")
    .toUpperCase();
function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
function Empty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Database size={24} />
      </div>
      <h3>{title}</h3>
      <p>{hint || "Dữ liệu của bạn sẽ xuất hiện tại đây."}</p>
    </div>
  );
}
function DataState({ error, loading }: { error: string; loading: boolean }) {
  return error ? (
    <p className="error" role="alert">
      {error}
    </p>
  ) : loading ? (
    <p className="muted loading">
      <Loader2 size={15} className="spin" /> Đang tải dữ liệu…
    </p>
  ) : null;
}
function Field({ title, children }: { title: string; children: ReactNode }) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{title}</label>
      {isValidElement(children)
        ? cloneElement(children as ReactElement<{ id?: string }>, { id })
        : children}
    </div>
  );
}
function Select({
  id,
  name,
  options,
  defaultValue,
  onChange,
}: {
  id?: string;
  name: string;
  options: readonly string[];
  defaultValue?: string;
  onChange?: (v: string) => void;
}) {
  return (
    <select
      id={id}
      name={name}
      defaultValue={defaultValue}
      onChange={(e) => onChange?.(e.target.value)}
    >
      {options.map((v) => (
        <option key={v} value={v}>
          {labels[v] || v}
        </option>
      ))}
    </select>
  );
}
function Modal({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: ReactNode;
}) {
  const modalRef = useRef<HTMLElement>(null);
  const closeRef = useRef(close);
  closeRef.current = close;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const focusable = () =>
      Array.from(
        modalRef.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], summary, [tabindex="0"]',
        ) || [],
      ).filter((el) => el.getClientRects().length > 0);
    const first =
      focusable().find((el) =>
        ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName),
      ) || focusable()[0];
    first?.focus();
    const fn = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeRef.current();
      if (e.key === "Tab") {
        const items = focusable();
        const first = items[0],
          last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    window.addEventListener("keydown", fn);
    return () => {
      window.removeEventListener("keydown", fn);
      if (previous?.isConnected) previous.focus();
    };
  }, []);
  return (
    <div className="modal-backdrop" onClick={close}>
      <section
        ref={modalRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <header>
          <h2>{title}</h2>
          <button className="icon-button" aria-label="Đóng" onClick={close}>
            <X size={20} />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>("overview"),
    [ready, setReady] = useState(false),
    [online, setOnline] = useState(false),
    [version, setVersion] = useState(0),
    [busy, setBusy] = useState(false);
  const [connection, setConnection] = useState<Connection>({
      baseUrl: "http://127.0.0.1:8765",
      token: "",
    }),
    [notice, setNotice] = useState<{ text: string; error: boolean } | null>(
      null,
    );
  const [query, setQuery] = useState(""),
    [searching, setSearching] = useState(false),
    [results, setResults] = useState<
      {
        entity_id: string;
        entity_type: string;
        title: string;
        snippet: string;
        person_id?: string | null;
      }[]
    >([]),
    [focusPerson, setFocusPerson] = useState<string | null>(null),
    [focusPost, setFocusPost] = useState<string | null>(null);
  const act: Act = async (work, message = "Đã lưu thay đổi") => {
    if (busy) return;
    setBusy(true);
    setNotice(null);
    try {
      const result = await work();
      if (message && result !== false)
        setNotice({ text: message, error: false });
    } catch (e) {
      setNotice({
        text: e instanceof Error ? e.message : "Có lỗi xảy ra",
        error: true,
      });
    } finally {
      setVersion((v) => v + 1);
      setBusy(false);
    }
  };
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        let next = await desktopConnection();
        if (!next) {
          const saved = sessionStorage.getItem("scansocial-connection");
          if (saved) next = JSON.parse(saved) as Connection;
        }
        if (!next) return;
        configure(next);
        if (active) setConnection(next);
        for (let i = 0; i < 30 && active; i++) {
          try {
            await request("/dashboard");
            if (active) setReady(true);
            return;
          } catch {
            await new Promise((resolve) => setTimeout(resolve, 500));
          }
        }
        if (active)
          setNotice({
            text: "Chưa kết nối được engine. Kiểm tra dịch vụ và session token.",
            error: true,
          });
      } catch (e) {
        if (active) setNotice({ text: String(e), error: true });
      }
    })();
    return () => {
      active = false;
    };
  }, []);
  useEffect(
    () =>
      ready
        ? liveFeed((type) => {
            setVersion((v) => v + 1);
            if (type === "CARE_TASK_DUE")
              setNotice({
                text: "Có lịch chăm sóc đến hạn. Mở Lịch chăm sóc để xử lý.",
                error: false,
              });
          }, setOnline)
        : undefined,
    [ready],
  );
  useEffect(() => {
    if (!notice || notice.error) return;
    const timer = setTimeout(() => setNotice(null), 5000);
    return () => clearTimeout(timer);
  }, [notice]);
  const props = { version, act, busy };
  const openPerson = (id: string) => {
    setFocusPerson(id);
    setPage("contacts");
  };
  async function search(e: FormEvent) {
    e.preventDefault();
    setSearching(true);
    try {
      const found = await request<typeof results>(
        `/search?q=${encodeURIComponent(query)}`,
      );
      setResults(found);
      if (!found.length)
        setNotice({ text: "Không tìm thấy kết quả phù hợp.", error: false });
    } catch (e) {
      setNotice({ text: String(e), error: true });
    } finally {
      setSearching(false);
    }
  }
  const current = nav.find((n) => n.id === page)!;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("overview");
          }}
        >
          <span className="brand-mark">
            <Radar size={25} />
          </span>
          <span>
            ScanSocial<small>LEAD INTELLIGENCE</small>
          </span>
        </a>
        <div className="workspace-tag">
          <span className="workspace-avatar">S</span>
          <div>
            Không gian của bạn<small>Local workspace</small>
          </div>
          <ChevronRight size={14} />
        </div>
        <span className="nav-label">KHÔNG GIAN LÀM VIỆC</span>
        <nav>
          {nav.map((n) => (
            <button
              key={n.id}
              className={page === n.id ? "active" : ""}
              onClick={() => setPage(n.id)}
            >
              <n.icon size={19} />
              {n.title}
              {page === n.id && <span className="active-dot" />}
            </button>
          ))}
        </nav>
        <div className="local-card">
          <Shield size={22} />
          <strong>Dữ liệu ở bên bạn.</strong>
          <p>
            CRM được lưu trên máy.
            <br />
            Bạn quản lý quyền chia sẻ.
          </p>
          <Badge tone="dark">LOCAL FIRST</Badge>
        </div>
        <div className="sidebar-footer">
          <span className={`status-dot ${online ? "online" : ""}`} />
          {online ? "Engine đã kết nối" : "Chưa có kết nối trực tiếp"}
          <small>ScanSocial v0.1.0</small>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <span className="breadcrumb">
            Không gian làm việc <ChevronRight size={14} />{" "}
            <strong>{current.title}</strong>
          </span>
          <form className="global-search" onSubmit={search}>
            <Search size={17} />
            <input
              aria-label="Tìm kiếm toàn bộ"
              placeholder="Tìm tên, SĐT, nội dung…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button
              disabled={!ready || !query.trim() || searching}
              aria-label="Tìm kiếm"
            >
              {searching ? (
                <Loader2 className="spin" size={17} />
              ) : (
                <ArrowRight size={17} />
              )}
            </button>
          </form>
          <span className="user-avatar">ME</span>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">SCANSOCIAL WORKSPACE</div>
              <h1>{current.title}</h1>
              <p>
                {
                  {
                    overview: "Từ tín hiệu quan tâm đến mối quan hệ dài lâu.",
                    leads: "Tìm nhu cầu thật. Hiểu lý do đằng sau mỗi điểm số.",
                    contacts: "Một hồ sơ thống nhất cho mỗi mối quan hệ.",
                    pipeline:
                      "Theo sát từng cơ hội, từ lần gặp đầu đến thành công.",
                    care: "Đúng người, đúng thời điểm, đúng bước tiếp theo.",
                    zalo: "Lưu ngữ cảnh, soạn phản hồi và gửi thủ công trên Zalo.",
                    campaigns:
                      "Soạn đợt chăm sóc, kiểm tra quyền liên hệ và duyệt tin OA.",
                    blacklist:
                      "Giữ lại tín hiệu hữu ích, giảm nội dung không phù hợp.",
                    settings:
                      "Kết nối nguồn dữ liệu và bảo vệ công việc của bạn.",
                  }[page]
                }
              </p>
            </div>
            <button
              className="button secondary"
              disabled={!ready || busy}
              onClick={() => setVersion((v) => v + 1)}
            >
              <RefreshCw size={16} />
              Làm mới
            </button>
          </div>
          {notice && (
            <div
              className={`notice ${notice.error ? "error" : ""}`}
              role={notice.error ? "alert" : "status"}
            >
              <span>{notice.text}</span>
              <button
                aria-label="Đóng thông báo"
                onClick={() => setNotice(null)}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {!ready ? (
            <section className="panel connect-panel">
              <div className="empty-icon">
                <Wifi size={30} />
              </div>
              <h2>Kết nối không gian làm việc</h2>
              <p>Khởi động engine trên máy rồi nhập session token để mở CRM.</p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const form = e.currentTarget;
                  void act(async () => {
                    const next = {
                      baseUrl: value(form, "baseUrl"),
                      token: value(form, "token"),
                    };
                    configure(next);
                    await request("/dashboard");
                    setConnection(next);
                    sessionStorage.setItem(
                      "scansocial-connection",
                      JSON.stringify(next),
                    );
                    setReady(true);
                  }, "Đã kết nối engine");
                }}
              >
                <Field title="Địa chỉ engine">
                  <input
                    name="baseUrl"
                    defaultValue={connection.baseUrl}
                    required
                  />
                </Field>
                <Field title="Session token">
                  <input
                    type="password"
                    name="token"
                    autoComplete="off"
                    required
                    defaultValue={connection.token}
                  />
                </Field>
                <button className="button" disabled={busy}>
                  {busy ? "Đang kết nối…" : "Kết nối workspace"}
                  <ArrowRight size={16} />
                </button>
              </form>
              <code>python scripts/dev.py</code>
              <small>Token chỉ được lưu trong phiên trình duyệt này.</small>
            </section>
          ) : (
            <>
              {page === "overview" && <Overview {...props} go={setPage} />}
              {page === "leads" && (
                <Leads
                  {...props}
                  focusPost={focusPost}
                  clearFocus={() => setFocusPost(null)}
                  openPerson={openPerson}
                />
              )}
              {page === "contacts" && (
                <Contacts
                  {...props}
                  focusPerson={focusPerson}
                  clearFocus={() => setFocusPerson(null)}
                />
              )}
              {page === "pipeline" && (
                <Pipeline {...props} openPerson={openPerson} />
              )}
              {page === "care" && <Care {...props} />}
              {page === "zalo" && <Zalo {...props} openPerson={openPerson} />}
              {page === "campaigns" && <Campaigns {...props} />}
              {page === "blacklist" && <Blacklist {...props} />}
              {page === "settings" && (
                <Preferences
                  {...props}
                  disconnect={() => {
                    setReady(false);
                    sessionStorage.removeItem("scansocial-connection");
                  }}
                />
              )}
            </>
          )}
        </main>
        <footer className="main-footer">
          <Shield size={13} />
          Dữ liệu CRM được lưu trên thiết bị{" "}
          <span>Được xây dựng cho những mối quan hệ tốt hơn.</span>
        </footer>
      </div>
      {results.length > 0 && (
        <Modal title="Kết quả tìm kiếm" close={() => setResults([])}>
          <div className="search-results">
            {results.map((r) => (
              <button
                key={`${r.entity_type}-${r.entity_id}`}
                onClick={() => {
                  if (r.entity_type === "PERSON") openPerson(r.entity_id);
                  if (r.person_id) openPerson(r.person_id);
                  if (r.entity_type === "POST") {
                    setPage("leads");
                    setFocusPost(r.entity_id);
                  }
                  setResults([]);
                }}
              >
                <Badge>{r.entity_type}</Badge>
                <strong>{r.title}</strong>
                <p>{r.snippet.replace(/<\/?b>/g, "")}</p>
              </button>
            ))}
          </div>
        </Modal>
      )}
      {searching === false && query && results.length === 0 && (
        <span className="sr-only">Chưa có kết quả tìm kiếm</span>
      )}
    </div>
  );
}

type Common = { version: number; act: Act; busy: boolean };
function Overview({ version, go }: Common & { go: (p: Page) => void }) {
  const summary = useData<{
    posts: number;
    persons: number;
    customers: number;
    overdue: number;
    active_scans: number;
  }>("/dashboard", version);
  const tasks = useData<Task[]>(
    "/care-tasks?status_filter=PENDING&limit=5",
    version,
  );
  const posts = useData<Post[]>("/posts?lead_score_min=55&limit=4", version);
  const metrics = [
    {
      title: "Tín hiệu đã phân tích",
      value: summary.data?.posts,
      icon: Radar,
      note: "Bài viết trong workspace",
    },
    {
      title: "Hồ sơ liên hệ",
      value: summary.data?.persons,
      icon: Users,
      note: "Hồ sơ chưa hợp nhất",
    },
    {
      title: "Khách hàng CRM",
      value: summary.data?.customers,
      icon: Target,
      note: "Mối quan hệ đang quản lý",
    },
    {
      title: "Lịch quá hạn",
      value: summary.data?.overdue,
      icon: CalendarDays,
      note: "Cần chăm sóc ngay",
    },
  ];
  return (
    <>
      <DataState {...summary} />
      <div className="metrics">
        {metrics.map((m) => (
          <article className="metric" key={m.title}>
            <div>
              <span>{m.title}</span>
              <m.icon size={19} />
            </div>
            <strong>{m.value ?? "—"}</strong>
            <small>{m.note}</small>
          </article>
        ))}
      </div>
      <section className="hero-panel">
        <div>
          <Badge tone="dark">LÀM VIỆC CÓ NGỮ CẢNH</Badge>
          <h2>
            Cơ hội tốt bắt đầu
            <br />
            từ việc hiểu khách hàng.
          </h2>
          <p>
            Nhập dữ liệu nguồn, lọc nhu cầu và bắt đầu
            <br />
            chăm sóc bằng một hồ sơ đầy đủ.
          </p>
          <button className="button light" onClick={() => go("leads")}>
            Khám phá lead
            <ArrowRight size={17} />
          </button>
        </div>
        <div className="signal-visual" aria-hidden="true">
          <div className="orbit o1" />
          <div className="orbit o2" />
          <div className="orbit o3" />
          <span className="signal-center">
            <Radar size={44} />
          </span>
          <span className="signal-chip c1">
            <Users size={16} />
            Khách hàng 360
          </span>
          <span className="signal-chip c2">
            <CheckCircle2 size={16} />
            Nhu cầu rõ ràng
          </span>
          <span className="signal-chip c3">
            <CalendarDays size={16} />
            Đúng thời điểm
          </span>
        </div>
      </section>
      <div className="two-columns">
        <section className="panel">
          <div className="section-heading">
            <h2>Lịch chăm sóc tiếp theo</h2>
            <button className="text-button" onClick={() => go("care")}>
              Xem tất cả
              <ArrowRight size={15} />
            </button>
          </div>
          <DataState {...tasks} />
          {tasks.data?.length ? (
            tasks.data.map((t) => (
              <div className="list-row" key={t.id}>
                <div className={`row-icon ${t.is_overdue ? "warning" : ""}`}>
                  <CalendarDays size={18} />
                </div>
                <div>
                  <strong>{t.title}</strong>
                  <small>{date(t.scheduled_at)}</small>
                </div>
                <Badge tone={t.is_overdue ? "warning" : ""}>
                  {t.is_overdue ? "Quá hạn" : labels[t.priority]}
                </Badge>
              </div>
            ))
          ) : (
            <Empty
              title="Bạn chưa có lịch chăm sóc"
              hint="Tạo khách hàng và lên lịch cho lần liên hệ tiếp theo."
            />
          )}
        </section>
        <section className="panel">
          <div className="section-heading">
            <h2>Lead đáng chú ý</h2>
            <button className="text-button" onClick={() => go("leads")}>
              Khám phá
              <ArrowRight size={15} />
            </button>
          </div>
          <DataState {...posts} />
          {posts.data?.length ? (
            posts.data.map((p) => (
              <div className="list-row" key={p.id}>
                <span className="avatar">{initials(p.author_name)}</span>
                <div>
                  <strong>{p.author_name}</strong>
                  <small className="truncate">{p.content}</small>
                </div>
                <span className="score">{p.lead_score}</span>
              </div>
            ))
          ) : (
            <Empty
              title="Chưa có lead đủ điểm"
              hint="Lead có điểm từ 55 sẽ xuất hiện tại đây."
            />
          )}
        </section>
      </div>
    </>
  );
}

function Leads({
  version,
  act,
  busy,
  openPerson,
  focusPost,
  clearFocus,
}: Common & {
  openPerson: (id: string) => void;
  focusPost: string | null;
  clearFocus: () => void;
}) {
  const [minimum, setMinimum] = useState("0"),
    [saved, setSaved] = useState(""),
    [offset, setOffset] = useState(0),
    [selected, setSelected] = useState<string | null>(null),
    [modal, setModal] = useState<"scan" | "import" | null>(null),
    [input, setInput] = useState("");
  useEffect(() => {
    if (focusPost) {
      setSelected(focusPost);
      clearFocus();
    }
  }, [focusPost]);
  const posts = useData<Post[]>(
    `/posts?limit=20&offset=${offset}&lead_score_min=${minimum}${saved ? `&is_saved=${saved}` : ""}`,
    version,
  );
  const jobs = useData<Job[]>("/scans?limit=5", version);
  const detail = useData<Post>(selected ? `/posts/${selected}` : null, version),
    analysis = useData<Analysis>(
      selected ? `/posts/${selected}/analysis` : null,
      version,
    ),
    comments = useData<Comment[]>(
      selected ? `/posts/${selected}/comments` : null,
      version,
    );
  const sample = () =>
    setInput(
      JSON.stringify(
        {
          platform: "FACEBOOK",
          posts: [
            {
              platform: "FACEBOOK",
              external_id: `example-${Date.now()}`,
              url: "https://www.facebook.com/example-post",
              author_name: "Nguyễn Minh Anh",
              content:
                "Nhà mình 3 tầng ở Hà Nội, cần lắp wifi và camera gấp hôm nay. Tư vấn giúp mình nhé!",
              posted_at: new Date().toISOString(),
              comments: [],
            },
          ],
        },
        null,
        2,
      ),
    );
  return (
    <>
      <div className="toolbar">
        <div className="filter-group">
          <Select
            name="minimum"
            options={["0", "40", "55", "70"]}
            onChange={(v) => {
              setMinimum(v);
              setOffset(0);
            }}
          />
          <select
            aria-label="Lọc bài đã lưu"
            value={saved}
            onChange={(e) => {
              setSaved(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">Tất cả bài viết</option>
            <option value="true">Đã lưu</option>
            <option value="false">Chưa lưu</option>
          </select>
        </div>
        <div className="actions">
          <button
            className="button secondary"
            onClick={() => setModal("import")}
          >
            <FileJson size={16} />
            Nhập JSON
          </button>
          <button className="button" onClick={() => setModal("scan")}>
            <Plus size={17} />
            Tạo lượt quét
          </button>
        </div>
      </div>
      {jobs.data?.length ? (
        <div className="jobs">
          {jobs.data.map((j) => (
            <article className="job" key={j.id}>
              <div>
                <Badge tone={j.status === "FAILED" ? "warning" : "green"}>
                  {labels[j.status] || j.status}
                </Badge>
                <strong>
                  {labels[j.platform]} ·{" "}
                  {j.keywords.join(", ") || "Nhập dữ liệu"}
                </strong>
                <small>
                  {j.scanned_count} đã xem · {j.matched_count} nhận ·{" "}
                  {j.qualified_count} đủ điểm
                </small>
                {j.error_message && <p className="error">{j.error_message}</p>}
              </div>
              <div className="actions">
                {["RUNNING", "PAUSED"].includes(j.status) && (
                  <>
                    <button
                      className="button secondary compact"
                      disabled={busy}
                      onClick={() =>
                        void act(() =>
                          request(
                            `/scans/${j.id}/${j.status === "PAUSED" ? "resume" : "pause"}`,
                            "POST",
                          ),
                        )
                      }
                    >
                      {j.status === "PAUSED" ? "Tiếp tục" : "Tạm dừng"}
                    </button>
                    <button
                      className="button secondary compact"
                      disabled={busy}
                      onClick={() =>
                        void act(() => request(`/scans/${j.id}/stop`, "POST"))
                      }
                    >
                      Dừng
                    </button>
                  </>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : null}
      <section className="panel">
        <div className="section-heading">
          <h2>Tín hiệu từ cộng đồng</h2>
          <Badge>ĐIỂM 0–100</Badge>
        </div>
        <DataState {...posts} />
        {posts.data?.length ? (
          <div className="lead-grid">
            {posts.data.map((p) => (
              <article className="lead-card" key={p.id}>
                <div className="lead-author">
                  <span className="avatar">{initials(p.author_name)}</span>
                  <div>
                    <strong>{p.author_name}</strong>
                    <small>
                      {labels[p.platform]} · {date(p.posted_at)}
                    </small>
                  </div>
                  <span className={`score ${p.lead_score >= 55 ? "high" : ""}`}>
                    {p.lead_score}
                  </span>
                </div>
                <p>{p.content}</p>
                <div className="lead-meta">
                  <Badge tone={p.urgency === "HIGH" ? "warning" : ""}>
                    Ưu tiên {labels[p.urgency]?.toLowerCase()}
                  </Badge>
                  {p.phone_extracted && <Badge tone="green">Có SĐT</Badge>}
                  {p.is_saved && <Bookmark size={14} />}
                </div>
                <div className="lead-actions">
                  <button
                    className="text-button"
                    onClick={() => setSelected(p.id)}
                  >
                    Xem phân tích
                    <ArrowRight size={15} />
                  </button>
                  <button
                    className="icon-button"
                    aria-label={p.is_saved ? "Bỏ lưu bài" : "Lưu bài"}
                    disabled={busy}
                    onClick={() =>
                      void act(
                        () =>
                          request(
                            `/posts/${p.id}/save`,
                            p.is_saved ? "DELETE" : "POST",
                          ),
                        p.is_saved
                          ? "Đã bỏ lưu"
                          : "Đã lưu bài và bảo vệ khỏi tự động dọn dẹp",
                      )
                    }
                  >
                    <Bookmark
                      size={18}
                      fill={p.is_saved ? "currentColor" : "none"}
                    />
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <Empty
            title="Chưa có tín hiệu trong bộ lọc này"
            hint="Nhập JSON dữ liệu được phép sử dụng hoặc kết nối nguồn để bắt đầu."
          />
        )}
        <div className="pagination">
          <button
            disabled={!offset}
            onClick={() => setOffset((n) => Math.max(0, n - 20))}
          >
            ← Trước
          </button>
          <span>Trang {offset / 20 + 1}</span>
          <button
            disabled={!posts.data || posts.data.length < 20}
            onClick={() => setOffset((n) => n + 20)}
          >
            Tiếp →
          </button>
        </div>
      </section>
      {modal && (
        <Modal
          title={modal === "scan" ? "Tạo lượt quét" : "Nhập dữ liệu nguồn"}
          close={() => setModal(null)}
        >
          {modal === "scan" ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = e.currentTarget;
                void act(async () => {
                  await request("/scans", "POST", {
                    platform: value(f, "platform"),
                    keywords: value(f, "keywords")
                      .split(",")
                      .map((x) => x.trim())
                      .filter(Boolean),
                    max_posts: Number(value(f, "maximum")),
                    max_age_hours: Number(value(f, "age")),
                  });
                  setModal(null);
                }, "Đã tạo tác vụ quét");
              }}
            >
              <Field title="Nguồn">
                <Select name="platform" options={["FACEBOOK", "THREADS"]} />
              </Field>
              <Field title="Từ khóa (cách nhau bằng dấu phẩy)">
                <input
                  name="keywords"
                  required
                  placeholder="cần lắp wifi, camera"
                />
              </Field>
              <div className="form-grid">
                <Field title="Số bài tối đa">
                  <input
                    type="number"
                    name="maximum"
                    min="1"
                    max="5000"
                    defaultValue="100"
                    required
                  />
                </Field>
                <Field title="Tuổi bài tối đa (giờ)">
                  <input
                    type="number"
                    name="age"
                    min="1"
                    max="168"
                    defaultValue="24"
                    required
                  />
                </Field>
              </div>
              <p className="muted">
                Cần access token có quyền phù hợp trong Cài đặt. Facebook đọc
                feed của Page đã cấu hình.
              </p>
              <button className="button" disabled={busy}>
                Bắt đầu quét
              </button>
            </form>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void act(async () => {
                  const payload = JSON.parse(input);
                  const result = await request<Job>(
                    "/scans/import",
                    "POST",
                    payload,
                  );
                  setModal(null);
                  setInput("");
                  return result;
                }, "Đã nhập và phân tích dữ liệu");
              }}
            >
              <p className="muted">
                Nhập bài viết và bình luận từ dữ liệu bạn có quyền sử dụng. Bài
                trùng, quá cũ và blacklist cứng sẽ được bỏ qua.
              </p>
              <div className="actions">
                <label className="button secondary compact">
                  Chọn file JSON
                  <input
                    className="sr-only"
                    type="file"
                    accept=".json,application/json"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file)
                        void act(async () => {
                          if (file.size > 10 * 1024 * 1024)
                            throw new Error("File tối đa 10 MB");
                          setInput(await file.text());
                        }, "");
                    }}
                  />
                </label>
                <button className="text-button" type="button" onClick={sample}>
                  Điền ví dụ
                </button>
              </div>
              <Field title="Nội dung JSON">
                <textarea
                  className="code-input"
                  rows={13}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  required
                />
              </Field>
              <button className="button" disabled={busy}>
                Nhập & phân tích
                <ArrowRight size={16} />
              </button>
            </form>
          )}
        </Modal>
      )}
      {selected && (
        <Modal title="Phân tích tín hiệu" close={() => setSelected(null)}>
          <DataState {...detail} />
          {detail.data && (
            <>
              <div className="section-heading">
                <div>
                  <h3>{detail.data.author_name}</h3>
                  <small>{date(detail.data.posted_at)}</small>
                </div>
                <button
                  className="text-button"
                  disabled={!sourceUrl(detail.data.url) || busy}
                  onClick={() =>
                    void act(() => openSource(detail.data!.url), "")
                  }
                >
                  Nguồn
                  <ExternalLink size={14} />
                </button>
              </div>
              <p className="post-content">{detail.data.content}</p>
              <DataState {...analysis} />
              {analysis.data && (
                <>
                  <div className="score-grid">
                    {[
                      ["Ý định", analysis.data.score.intent_score],
                      ["Khẩn cấp", analysis.data.score.urgency_score],
                      ["Cơ hội", analysis.data.score.opportunity_score],
                      ["Spam", analysis.data.score.spam_score],
                    ].map(([name, n]) => (
                      <div key={name}>
                        <small>{name}</small>
                        <strong>{n}</strong>
                      </div>
                    ))}
                  </div>
                  <div className="recommendation">
                    <Activity size={20} />
                    <div>
                      <strong>{analysis.data.score.next_best_action}</strong>
                      <p>{analysis.data.score.action_reason}</p>
                    </div>
                  </div>
                  <details>
                    <summary>Lý do chấm điểm</summary>
                    {analysis.data.score.breakdown.map((b, i) => (
                      <p key={i}>
                        {b.points > 0 ? "+" : ""}
                        {b.points} · {b.reason}
                      </p>
                    ))}
                  </details>
                </>
              )}
              <button
                className="button"
                disabled={busy}
                onClick={() =>
                  void act(async () => {
                    const r = await request<{ person_id: string }>(
                      `/posts/${selected}/promote`,
                      "POST",
                    );
                    setSelected(null);
                    openPerson(r.person_id);
                  }, "Đã tạo hồ sơ liên hệ")
                }
              >
                <Users size={16} />
                Lưu vào khách hàng 360
              </button>
              <h3 className="spaced">
                Bình luận ({comments.data?.length || 0})
              </h3>
              <button
                className="text-button"
                disabled={busy}
                onClick={() =>
                  void act(
                    () => request(`/posts/${selected}/sync-comments`, "POST"),
                    "Đã đồng bộ bình luận từ API chính thức",
                  )
                }
              >
                Đồng bộ bình luận từ nguồn
              </button>
              {comments.data?.map((c) => (
                <div className="comment" key={c.id}>
                  <strong>{c.author_name}</strong>
                  <p>{c.content}</p>
                  <Badge>Ý định {c.intent_score}</Badge>
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() =>
                      void act(async () => {
                        const r = await request<{ person_id: string }>(
                          `/posts/${selected}/comments/${c.id}/promote`,
                          "POST",
                        );
                        setSelected(null);
                        openPerson(r.person_id);
                      })
                    }
                  >
                    Tạo liên hệ từ bình luận
                  </button>
                </div>
              ))}
            </>
          )}
        </Modal>
      )}
    </>
  );
}

function Contacts({
  version,
  act,
  busy,
  focusPerson,
  clearFocus,
}: Common & { focusPerson: string | null; clearFocus: () => void }) {
  const [selected, setSelected] = useState<string | null>(null),
    [create, setCreate] = useState(false),
    [filter, setFilter] = useState(""),
    [nameQuery, setNameQuery] = useState("");
  useEffect(() => {
    if (focusPerson) {
      setSelected(focusPerson);
      clearFocus();
    }
  }, [focusPerson]);
  const persons = useData<Person[]>(
    `/persons?limit=500${filter ? `&has_phone=${filter}` : ""}`,
    version,
  );
  const profile = useData<Profile>(
    selected ? `/persons/${selected}` : null,
    version,
  );
  const customer = useData<Customer360>(
    profile.data?.customer_id ? `/customers/${profile.data.customer_id}` : null,
    version,
  );
  const shown = persons.data?.filter((p) =>
    p.display_name.toLocaleLowerCase().includes(nameQuery.toLocaleLowerCase()),
  );
  return (
    <>
      <div className="toolbar">
        <div className="filter-group">
          <div className="input-icon">
            <Search size={16} />
            <input
              placeholder="Lọc tên trong danh sách"
              aria-label="Lọc tên liên hệ"
              value={nameQuery}
              onChange={(e) => setNameQuery(e.target.value)}
            />
          </div>
          <select
            value={filter}
            aria-label="Lọc số điện thoại"
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="">Tất cả liên hệ</option>
            <option value="true">Có SĐT</option>
            <option value="false">Chưa có SĐT</option>
          </select>
        </div>
        <button className="button" onClick={() => setCreate(true)}>
          <Plus size={16} />
          Thêm liên hệ
        </button>
      </div>
      <div className={`crm-layout ${selected ? "has-detail" : ""}`}>
        <section className="panel">
          <div className="section-heading">
            <h2>Danh bạ của bạn</h2>
            <Badge>{shown?.length ?? 0} HỒ SƠ</Badge>
          </div>
          <DataState {...persons} />
          {shown?.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Liên hệ</th>
                    <th>Số điện thoại</th>
                    <th>Loại hồ sơ</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {shown.map((p) => (
                    <tr
                      key={p.id}
                      className={selected === p.id ? "selected" : ""}
                    >
                      <td>
                        <button
                          className="contact-name"
                          onClick={() => setSelected(p.id)}
                        >
                          <span className="avatar small">
                            {initials(p.display_name)}
                          </span>
                          <span>
                            <strong>{p.display_name}</strong>
                            <small>
                              {labels[p.source_type] || p.source_type}
                            </small>
                          </span>
                        </button>
                      </td>
                      <td>{p.phones.join(", ") || "Chưa có"}</td>
                      <td>
                        <Badge tone={p.is_customer ? "green" : ""}>
                          {p.is_customer ? "Khách hàng" : "Liên hệ"}
                        </Badge>
                      </td>
                      <td>
                        <button
                          className="icon-button"
                          aria-label={`Mở ${p.display_name}`}
                          onClick={() => setSelected(p.id)}
                        >
                          <ChevronRight size={17} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              title="Chưa có hồ sơ liên hệ"
              hint="Thêm thủ công hoặc lưu một lead từ Khám phá lead."
            />
          )}
        </section>
        {selected && (
          <section className="panel profile-panel">
            <div className="section-heading">
              <h2>Hồ sơ 360</h2>
              <button
                className="icon-button"
                aria-label="Đóng hồ sơ"
                onClick={() => setSelected(null)}
              >
                <X size={18} />
              </button>
            </div>
            <DataState {...profile} />
            {profile.data && (
              <>
                <div className="profile-header">
                  <span className="avatar large">
                    {initials(profile.data.display_name)}
                  </span>
                  <h2>{profile.data.display_name}</h2>
                  <Badge tone="green">
                    {profile.data.customer_id
                      ? "Khách hàng CRM"
                      : "Liên hệ mới"}
                  </Badge>
                </div>
                <div className="phone-list">
                  {profile.data.phones.map((p) => (
                    <div key={p.normalized_phone}>
                      <strong>{p.normalized_phone}</strong>
                      <small>
                        {p.source_type} ·{" "}
                        {p.is_verified
                          ? "Đã xác minh"
                          : "Chưa xác minh chủ sở hữu"}
                      </small>
                      {p.source_url && (
                        <button
                          className="text-button"
                          disabled={!sourceUrl(p.source_url) || busy}
                          onClick={() =>
                            void act(() => openSource(p.source_url!), "")
                          }
                        >
                          Nguồn dữ liệu ↗
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                {!profile.data.customer_id && (
                  <details>
                    <summary>Chỉnh sửa liên hệ</summary>
                    <form
                      key={profile.data.id + profile.data.display_name}
                      onSubmit={(e) => {
                        e.preventDefault();
                        const f = e.currentTarget;
                        void act(
                          () =>
                            request(`/persons/${selected}`, "PATCH", {
                              display_name: value(f, "name"),
                              phone: value(f, "phone") || null,
                            }),
                          "Đã cập nhật liên hệ",
                        );
                      }}
                    >
                      <Field title="Tên liên hệ">
                        <input
                          name="name"
                          required
                          defaultValue={profile.data.display_name}
                          maxLength={255}
                        />
                      </Field>
                      <Field title="Thêm số điện thoại">
                        <input name="phone" placeholder="09xx xxx xxx" />
                      </Field>
                      <button
                        className="button secondary compact"
                        disabled={busy}
                      >
                        Lưu liên hệ
                      </button>
                    </form>
                  </details>
                )}
                {!profile.data.customer_id && (
                  <form
                    className="inset"
                    onSubmit={(e) => {
                      e.preventDefault();
                      const f = e.currentTarget;
                      void act(
                        () =>
                          request(
                            `/persons/${selected}/convert-customer`,
                            "POST",
                            {
                              need_type: value(f, "need"),
                              initial_opportunity_title:
                                value(f, "title") || null,
                              expected_revenue: Number(
                                value(f, "revenue") || 0,
                              ),
                            },
                          ),
                        "Đã chuyển thành khách hàng",
                      );
                    }}
                  >
                    <h3>Đưa vào CRM</h3>
                    <Field title="Nhu cầu">
                      <Select
                        name="need"
                        options={["WIFI", "CAMERA", "TV", "COMBO", "OTHER"]}
                      />
                    </Field>
                    <Field title="Cơ hội ban đầu (tùy chọn)">
                      <input name="title" placeholder="Lắp WiFi cho nhà mới" />
                    </Field>
                    <Field title="Giá trị dự kiến (VND)">
                      <input
                        name="revenue"
                        type="number"
                        min="0"
                        defaultValue="0"
                      />
                    </Field>
                    <button className="button" disabled={busy}>
                      Chuyển thành khách hàng
                      <ArrowRight size={15} />
                    </button>
                  </form>
                )}
                {customer.data && (
                  <>
                    <h3 className="spaced">Trạng thái khách hàng</h3>
                    <Select
                      key={customer.data.status}
                      name="status"
                      options={stages}
                      defaultValue={customer.data.status}
                      onChange={(status) =>
                        void act(() =>
                          request(
                            `/customers/${customer.data!.id}/status`,
                            "PATCH",
                            { status },
                          ),
                        )
                      }
                    />
                    <h3 className="spaced">Nhu cầu</h3>
                    <form
                      key={customer.data.id}
                      onSubmit={(e) => {
                        e.preventDefault();
                        const f = e.currentTarget;
                        void act(() =>
                          request(
                            `/customers/${customer.data!.id}/need-profile`,
                            "PUT",
                            {
                              need_type: value(f, "need"),
                              property_type: value(f, "property"),
                              province: value(f, "province") || null,
                              urgency: value(f, "urgency"),
                            },
                          ),
                        );
                      }}
                    >
                      <div className="form-grid">
                        <Field title="Dịch vụ">
                          <Select
                            name="need"
                            options={["WIFI", "CAMERA", "TV", "COMBO", "OTHER"]}
                            defaultValue={customer.data.need_type || "OTHER"}
                          />
                        </Field>
                        <Field title="Khẩn cấp">
                          <Select
                            name="urgency"
                            options={["LOW", "MEDIUM", "HIGH"]}
                            defaultValue={customer.data.urgency || "MEDIUM"}
                          />
                        </Field>
                      </div>
                      <Field title="Loại công trình">
                        <Select
                          name="property"
                          options={[
                            "UNKNOWN",
                            "HOUSE",
                            "APARTMENT",
                            "RENTAL",
                            "STORE",
                            "OFFICE",
                            "BUSINESS",
                          ]}
                          defaultValue={
                            customer.data.property_type || "UNKNOWN"
                          }
                        />
                      </Field>
                      <Field title="Tỉnh / thành">
                        <input
                          name="province"
                          defaultValue={customer.data.province || ""}
                        />
                      </Field>
                      <button
                        className="button secondary compact"
                        disabled={busy}
                      >
                        Lưu nhu cầu
                      </button>
                    </form>
                    <h3 className="spaced">Cơ hội bán hàng</h3>
                    {customer.data.opportunities.map((o) => (
                      <div className="list-row" key={o.id}>
                        <div>
                          <strong>{o.title}</strong>
                          <small>{money(o.expected_revenue)}</small>
                        </div>
                        <Badge>{labels[o.stage]}</Badge>
                      </div>
                    ))}
                    <form
                      className="inset"
                      onSubmit={(e) => {
                        e.preventDefault();
                        const f = e.currentTarget;
                        void act(async () => {
                          await request(
                            `/customers/${customer.data!.id}/opportunities`,
                            "POST",
                            {
                              title: value(f, "title"),
                              expected_revenue: Number(
                                value(f, "revenue") || 0,
                              ),
                            },
                          );
                          f.reset();
                        }, "Đã thêm cơ hội");
                      }}
                    >
                      <input
                        name="title"
                        placeholder="Tên cơ hội mới"
                        required
                      />
                      <input
                        name="revenue"
                        type="number"
                        min="0"
                        placeholder="Giá trị dự kiến"
                      />
                      <button
                        className="button secondary compact"
                        disabled={busy}
                      >
                        <Plus size={14} />
                        Thêm cơ hội
                      </button>
                    </form>
                  </>
                )}
                <h3 className="spaced">Ghi chú</h3>
                {profile.data.notes.map((n) => (
                  <div className="note" key={n.id}>
                    <p>{n.content}</p>
                    <small>{date(n.created_at)}</small>
                  </div>
                ))}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = e.currentTarget;
                    void act(async () => {
                      await request(`/persons/${selected}/notes`, "POST", {
                        content: value(f, "content"),
                      });
                      f.reset();
                    }, "Đã thêm ghi chú");
                  }}
                >
                  <textarea
                    name="content"
                    required
                    rows={3}
                    placeholder="Thông tin cần nhớ về khách hàng…"
                  />
                  <button className="button secondary compact" disabled={busy}>
                    Lưu ghi chú
                  </button>
                </form>
                <h3 className="spaced">Nhãn hồ sơ</h3>
                <form
                  key={`labels-${selected}-${profile.data.labels.join(",")}`}
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = e.currentTarget;
                    void act(() =>
                      request(`/persons/${selected}/labels`, "PUT", {
                        labels: value(f, "labels")
                          .split(",")
                          .map((v) => v.trim())
                          .filter(Boolean),
                      }),
                    );
                  }}
                >
                  <input
                    name="labels"
                    placeholder="VIP, Hà Nội, WiFi"
                    defaultValue={profile.data.labels.join(", ")}
                  />
                  <button className="button secondary compact" disabled={busy}>
                    Lưu nhãn
                  </button>
                </form>
                <details className="spaced">
                  <summary>Quyền liên hệ</summary>
                  <form
                    key={`consent-${selected}-${JSON.stringify(profile.data.permission)}`}
                    onSubmit={(e) => {
                      e.preventDefault();
                      const f = e.currentTarget;
                      void act(
                        () =>
                          request(`/persons/${selected}/permission`, "PUT", {
                            marketing_allowed: new FormData(f).has("marketing"),
                            zalo_allowed: new FormData(f).has("zalo"),
                            opt_out: new FormData(f).has("optout"),
                            do_not_contact: new FormData(f).has("dnc"),
                            source: value(f, "source"),
                          }),
                        "Đã cập nhật quyền liên hệ",
                      );
                    }}
                  >
                    {[
                      ["marketing", "Cho phép marketing", "marketing_allowed"],
                      ["zalo", "Cho phép Zalo OA", "zalo_allowed"],
                      ["optout", "Đã từ chối marketing", "opt_out"],
                      ["dnc", "Không liên hệ", "do_not_contact"],
                    ].map(([name, title, key]) => (
                      <label className="checkbox" key={name}>
                        <input
                          type="checkbox"
                          name={name}
                          defaultChecked={
                            profile.data!.permission[
                              key as keyof Profile["permission"]
                            ]
                          }
                        />
                        {title}
                      </label>
                    ))}
                    <Field title="Nguồn ghi nhận sự đồng ý">
                      <input
                        name="source"
                        required
                        placeholder="Khách hàng đồng ý ngày…"
                        maxLength={64}
                      />
                    </Field>
                    <button
                      className="button secondary compact"
                      disabled={busy}
                    >
                      Lưu quyền liên hệ
                    </button>
                  </form>
                </details>
                <details className="spaced">
                  <summary>Hợp nhất hồ sơ trùng</summary>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const f = e.currentTarget;
                      void act(async () => {
                        await request("/persons/merge", "POST", {
                          primary_person_id: selected,
                          duplicate_person_id: value(f, "duplicate"),
                          merge_reason: value(f, "reason"),
                        });
                        f.reset();
                      }, "Đã hợp nhất hồ sơ");
                    }}
                  >
                    <Field title="Hồ sơ cần nhập vào hồ sơ này">
                      <select name="duplicate" required>
                        <option value="">Chọn liên hệ trùng</option>
                        {persons.data
                          ?.filter((p) => p.id !== selected)
                          .map((p) => (
                            <option value={p.id} key={p.id}>
                              {p.display_name} · {p.phones.join(", ")}
                            </option>
                          ))}
                      </select>
                    </Field>
                    <Field title="Lý do xác nhận">
                      <input name="reason" required />
                    </Field>
                    <label className="checkbox">
                      <input type="checkbox" required />
                      Tôi xác nhận đây là cùng một người.
                    </label>
                    <button
                      className="button secondary compact"
                      disabled={busy}
                    >
                      Hợp nhất vào hồ sơ này
                    </button>
                  </form>
                </details>
                <h3 className="spaced">Dòng thời gian</h3>
                <div className="timeline">
                  {profile.data.timeline.map((t) => (
                    <div key={t.id}>
                      <strong>{t.title}</strong>
                      <small>{date(t.created_at)}</small>
                    </div>
                  ))}
                </div>
              </>
            )}
          </section>
        )}
      </div>
      {create && (
        <Modal title="Thêm liên hệ mới" close={() => setCreate(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = e.currentTarget;
              void act(async () => {
                const p = await request<{ id: string }>("/persons", "POST", {
                  display_name: value(f, "name"),
                  phone: value(f, "phone") || null,
                });
                setCreate(false);
                setSelected(p.id);
              }, "Đã tạo liên hệ");
            }}
          >
            <Field title="Họ tên">
              <input name="name" required maxLength={255} autoFocus />
            </Field>
            <Field title="Số điện thoại (tùy chọn)">
              <input name="phone" placeholder="09xx xxx xxx" />
            </Field>
            <button className="button" disabled={busy}>
              Tạo liên hệ
              <Plus size={16} />
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}

function Pipeline({
  version,
  act,
  busy,
  openPerson,
}: Common & { openPerson: (id: string) => void }) {
  const customers = useData<Customer[]>("/customers?limit=500", version);
  const [opps, setOpps] = useState<
      (Customer360["opportunities"][number] & {
        customer_name: string;
        person_id: string;
      })[]
    >([]),
    [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    if (customers.data)
      Promise.all(
        customers.data.map((c) => request<Customer360>(`/customers/${c.id}`)),
      )
        .then((rows) => {
          if (active) {
            setOpps(
              rows.flatMap((c) =>
                c.opportunities.map((o) => ({
                  ...o,
                  customer_name: c.display_name,
                  person_id: c.person_id,
                })),
              ),
            );
            setError("");
          }
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    return () => {
      active = false;
    };
  }, [customers.data]);
  return (
    <>
      <div className="pipeline-summary">
        <Badge tone="green">{opps.length} CƠ HỘI</Badge>
        <span>
          Tổng giá trị dự kiến{" "}
          <strong>
            {money(
              opps
                .filter((o) => o.stage !== "LOST")
                .reduce((n, o) => n + o.expected_revenue, 0),
            )}
          </strong>
        </span>
      </div>
      <DataState error={error || customers.error} loading={customers.loading} />
      <div className="kanban">
        {stages.map((stage) => (
          <section className="kanban-column" key={stage}>
            <header>
              <span className={`stage-dot stage-${stage.toLowerCase()}`} />
              <h3>{labels[stage]}</h3>
              <Badge>{opps.filter((o) => o.stage === stage).length}</Badge>
            </header>
            {opps
              .filter((o) => o.stage === stage)
              .map((o) => (
                <article className="opportunity" key={o.id}>
                  <button
                    className="text-button"
                    onClick={() => openPerson(o.person_id)}
                  >
                    {o.customer_name}
                    <ChevronRight size={14} />
                  </button>
                  <h3>{o.title}</h3>
                  <strong className="revenue">
                    {money(o.expected_revenue)}
                  </strong>
                  <select
                    aria-label={`Giai đoạn ${o.title}`}
                    value={o.stage}
                    disabled={busy}
                    onChange={(e) =>
                      void act(
                        () =>
                          request(`/opportunities/${o.id}`, "PATCH", {
                            title: o.title,
                            expected_revenue: o.expected_revenue,
                            stage: e.target.value,
                          }),
                        "Đã chuyển giai đoạn",
                      )
                    }
                  >
                    {stages.map((s) => (
                      <option key={s} value={s}>
                        {labels[s]}
                      </option>
                    ))}
                  </select>
                </article>
              ))}
            {!opps.some((o) => o.stage === stage) && (
              <p className="kanban-empty">Chưa có cơ hội</p>
            )}
          </section>
        ))}
      </div>
      <p className="muted">
        Thêm cơ hội trong hồ sơ Khách hàng 360. Chọn giai đoạn trên thẻ để cập
        nhật.
      </p>
    </>
  );
}

function Care({ version, act, busy }: Common) {
  const [filter, setFilter] = useState("PENDING"),
    [create, setCreate] = useState(false),
    [overdue, setOverdue] = useState(false);
  const tasks = useData<Task[]>(
      `/care-tasks?limit=200${filter ? `&status_filter=${filter}` : ""}`,
      version,
    ),
    customers = useData<Customer[]>("/customers?limit=500", version),
    proposals = useData<
      {
        customer_id: string;
        opportunity_id: string;
        recommended_title: string;
        suggested_time: string;
      }[]
    >("/care-tasks/proposals", version);
  const shown = tasks.data?.filter((t) => !overdue || t.is_overdue);
  return (
    <>
      <div className="toolbar">
        <div className="filter-group">
          <select
            aria-label="Trạng thái lịch chăm sóc"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="PENDING">Chờ chăm sóc</option>
            <option value="COMPLETED">Đã hoàn thành</option>
            <option value="">Tất cả</option>
          </select>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={overdue}
              onChange={(e) => setOverdue(e.target.checked)}
            />
            Chỉ quá hạn
          </label>
        </div>
        <button className="button" onClick={() => setCreate(true)}>
          <Plus size={16} />
          Tạo lịch chăm sóc
        </button>
      </div>
      {!!proposals.data?.length && (
        <section className="panel proposals">
          <h3>Đề xuất bước tiếp theo</h3>
          {proposals.data.map((p) => (
            <div className="list-row" key={p.opportunity_id}>
              <div>
                <strong>{p.recommended_title}</strong>
                <small>Báo giá chưa cập nhật sau 48 giờ</small>
              </div>
              <button
                className="button secondary compact"
                disabled={busy}
                onClick={() =>
                  void act(
                    () =>
                      request("/care-tasks", "POST", {
                        customer_id: p.customer_id,
                        opportunity_id: p.opportunity_id,
                        title: p.recommended_title,
                        scheduled_at: p.suggested_time.endsWith("Z")
                          ? p.suggested_time
                          : p.suggested_time + "Z",
                      }),
                    "Đã tạo lịch follow-up",
                  )
                }
              >
                Lên lịch
              </button>
            </div>
          ))}
        </section>
      )}
      <section className="panel">
        <div className="section-heading">
          <h2>Lịch hẹn & theo dõi</h2>
          <Badge>{shown?.length || 0} LỊCH</Badge>
        </div>
        <DataState {...tasks} />
        {shown?.length ? (
          shown.map((t) => (
            <article className="care-row" key={t.id}>
              <div className={`row-icon ${t.is_overdue ? "warning" : ""}`}>
                <CalendarDays size={22} />
              </div>
              <div className="care-info">
                <h3>{t.title}</h3>
                <p>
                  {customers.data?.find((c) => c.id === t.customer_id)
                    ?.display_name || "Khách hàng"}{" "}
                  · {date(t.scheduled_at)}
                </p>
                {t.description && <small>{t.description}</small>}
              </div>
              <Badge tone={t.is_overdue ? "warning" : ""}>
                {t.is_overdue ? "Quá hạn" : labels[t.priority]}
              </Badge>
              {t.status === "PENDING" ? (
                <button
                  className="button secondary compact"
                  disabled={busy}
                  onClick={() =>
                    void act(
                      () => request(`/care-tasks/${t.id}/complete`, "PATCH"),
                      "Đã hoàn thành lịch chăm sóc",
                    )
                  }
                >
                  <Check size={16} />
                  Hoàn thành
                </button>
              ) : (
                <Badge tone="green">Đã hoàn thành</Badge>
              )}
            </article>
          ))
        ) : (
          <Empty
            title="Không có lịch trong bộ lọc này"
            hint="Lên lịch để không bỏ lỡ lần chăm sóc tiếp theo."
          />
        )}
      </section>
      {create && (
        <Modal title="Tạo lịch chăm sóc" close={() => setCreate(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = e.currentTarget;
              void act(async () => {
                await request("/care-tasks", "POST", {
                  customer_id: value(f, "customer"),
                  title: value(f, "title"),
                  scheduled_at: new Date(value(f, "time")).toISOString(),
                  priority: value(f, "priority"),
                  description: value(f, "description") || null,
                });
                setCreate(false);
              }, "Đã tạo lịch chăm sóc");
            }}
          >
            <Field title="Khách hàng">
              <select name="customer" required>
                <option value="">Chọn khách hàng</option>
                {customers.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.display_name}
                  </option>
                ))}
              </select>
            </Field>
            <Field title="Việc cần làm">
              <input name="title" required maxLength={255} />
            </Field>
            <div className="form-grid">
              <Field title="Thời gian trên máy của bạn">
                <input type="datetime-local" name="time" required />
              </Field>
              <Field title="Ưu tiên">
                <Select name="priority" options={["MEDIUM", "HIGH", "LOW"]} />
              </Field>
            </div>
            <Field title="Ghi chú">
              <textarea name="description" rows={3} />
            </Field>
            <button className="button" disabled={busy}>
              Lưu lịch chăm sóc
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}

function Blacklist({ version, act, busy }: Common) {
  const rules = useData<Rule[]>("/blacklist", version);
  return (
    <div className="two-columns blacklist-layout">
      <section className="panel">
        <div className="section-heading">
          <h2>Quy tắc đang áp dụng</h2>
          <Shield size={19} />
        </div>
        <DataState {...rules} />
        {rules.data?.length ? (
          rules.data.map((r) => (
            <div className="list-row" key={r.id}>
              <div>
                <strong>{r.value}</strong>
                <small>
                  {r.entity_type} · {r.reason || "Không có ghi chú"}
                </small>
              </div>
              <Badge tone={r.mode === "HARD_BLACKLIST" ? "warning" : ""}>
                {r.mode === "HARD_BLACKLIST" ? "Loại bỏ" : "Giảm điểm"}
              </Badge>
              <button
                className="icon-button"
                aria-label={`Xóa quy tắc ${r.value}`}
                disabled={busy}
                onClick={() =>
                  void act(
                    () => request(`/blacklist/${r.id}`, "DELETE"),
                    "Đã xóa quy tắc",
                  )
                }
              >
                <X size={17} />
              </button>
            </div>
          ))
        ) : (
          <Empty
            title="Chưa có quy tắc blacklist"
            hint="Quy tắc được lưu và áp dụng cho các lần nhập hoặc quét tiếp theo."
          />
        )}
      </section>
      <section className="panel">
        <h2>Thêm bộ lọc</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = e.currentTarget;
            void act(async () => {
              await request("/blacklist", "POST", {
                entity_type: value(f, "type"),
                value: value(f, "value"),
                mode: value(f, "mode"),
                reason: value(f, "reason"),
              });
              f.reset();
            }, "Đã lưu quy tắc blacklist");
          }}
        >
          <Field title="Loại đối tượng">
            <Select
              name="type"
              options={[
                "KEYWORD",
                "PROFILE",
                "PAGE",
                "GROUP",
                "PHONE",
                "DOMAIN",
                "REGEX",
              ]}
            />
          </Field>
          <Field title="Giá trị">
            <input
              name="value"
              required
              maxLength={255}
              placeholder="Từ khóa, ID hồ sơ, SĐT, tên miền…"
            />
          </Field>
          <Field title="Hành động">
            <select name="mode">
              <option value="HARD_BLACKLIST">Loại bỏ ngay</option>
              <option value="SOFT_BLACKLIST">Giữ bài, giảm 80 điểm</option>
            </select>
          </Field>
          <Field title="Lý do">
            <input name="reason" maxLength={255} />
          </Field>
          <button className="button" disabled={busy}>
            <Plus size={16} />
            Lưu quy tắc
          </button>
        </form>
        <p className="muted spaced">
          Bộ lọc áp dụng trước khi chấm điểm. Blacklist cứng luôn được ưu tiên
          khi có nhiều quy tắc trùng nhau.
        </p>
      </section>
    </div>
  );
}

function Zalo({
  version,
  act,
  busy,
  openPerson,
}: Common & { openPerson: (id: string) => void }) {
  const conversations = useData<Conversation[]>("/conversations", version),
    persons = useData<Person[]>("/persons?limit=500", version);
  const [selected, setSelected] = useState<string | null>(null),
    [create, setCreate] = useState(false),
    [draft, setDraft] = useState("");
  const messages = useData<Message[]>(
    selected ? `/conversations/${selected}/messages` : null,
    version,
  );
  const conversation = conversations.data?.find((c) => c.id === selected);
  return (
    <>
      <div className="toolbar">
        <Badge tone="green">HỖ TRỢ 1:1 · GỬI THỦ CÔNG</Badge>
        <button className="button" onClick={() => setCreate(true)}>
          <Plus size={16} />
          Liên kết hội thoại
        </button>
      </div>
      <div className="zalo-layout">
        <section className="panel">
          <h2>Hội thoại đã liên kết</h2>
          <DataState {...conversations} />
          {conversations.data?.length ? (
            conversations.data.map((c) => (
              <button
                className={`conversation ${selected === c.id ? "selected" : ""}`}
                key={c.id}
                onClick={() => {
                  setSelected(c.id);
                  setDraft("");
                }}
              >
                <span className="avatar small">{initials(c.title)}</span>
                <div>
                  <strong>{c.title}</strong>
                  <small>{c.external_conversation_id}</small>
                </div>
                <ChevronRight size={15} />
              </button>
            ))
          ) : (
            <Empty
              title="Chưa có hội thoại"
              hint="Liên kết hội thoại Zalo với một hồ sơ CRM."
            />
          )}
        </section>
        <section className="panel">
          <div className="section-heading">
            <h2>{conversation?.title || "Trợ lý hội thoại"}</h2>
            {conversation && (
              <button
                className="text-button"
                onClick={() => openPerson(conversation.person_id)}
              >
                Hồ sơ 360
                <ArrowRight size={15} />
              </button>
            )}
          </div>
          {selected ? (
            <>
              <div className="messages">
                <DataState {...messages} />
                {messages.data?.map((m) => (
                  <div
                    key={m.id}
                    className={`message ${m.sender_type === "AGENT" ? "agent" : ""}`}
                  >
                    <Badge>
                      {m.sender_type === "AGENT" ? "Bạn" : "Khách hàng"}
                    </Badge>
                    <p>{m.content}</p>
                    <small>{date(m.sent_at)}</small>
                  </div>
                ))}
                {!messages.data?.length && (
                  <p className="muted">
                    Ghi nhận tin nhắn đã trao đổi để lưu ngữ cảnh.
                  </p>
                )}
              </div>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = e.currentTarget;
                  void act(async () => {
                    await request(
                      `/conversations/${selected}/messages`,
                      "POST",
                      {
                        content: value(f, "content"),
                        sender_type: value(f, "sender"),
                      },
                    );
                    f.reset();
                  }, "Đã ghi nhận tin nhắn (không gửi qua Zalo)");
                }}
              >
                <Field title="Tin nhắn đã trao đổi">
                  <textarea name="content" required rows={3} />
                </Field>
                <div className="actions">
                  <select name="sender">
                    <option value="CUSTOMER">Từ khách hàng</option>
                    <option value="AGENT">Từ bạn</option>
                  </select>
                  <button className="button secondary" disabled={busy}>
                    Ghi nhận tin nhắn
                  </button>
                </div>
              </form>
              <div className="draft-panel">
                <div className="section-heading">
                  <h3>Gợi ý phản hồi</h3>
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() =>
                      void act(async () => {
                        const r = await request<{ draft: string }>(
                          `/conversations/${selected}/suggestion`,
                          "POST",
                        );
                        setDraft(r.draft);
                      }, "Đã tạo bản nháp")
                    }
                  >
                    Soạn gợi ý<ArrowRight size={14} />
                  </button>
                </div>
                <textarea
                  aria-label="Bản nháp phản hồi"
                  rows={4}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  placeholder="Tạo gợi ý hoặc viết phản hồi của bạn…"
                />
                <button
                  className="button"
                  disabled={!draft || busy}
                  onClick={() =>
                    void act(
                      () => navigator.clipboard.writeText(draft),
                      "Đã sao chép. Mở Zalo và kiểm tra trước khi gửi.",
                    )
                  }
                >
                  Sao chép để gửi thủ công
                </button>
              </div>
            </>
          ) : (
            <Empty
              title="Chọn hội thoại để bắt đầu"
              hint="Gợi ý được soạn tại máy. Bạn kiểm tra và gửi trên Zalo."
            />
          )}
        </section>
      </div>
      {create && (
        <Modal title="Liên kết hội thoại Zalo" close={() => setCreate(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = e.currentTarget;
              void act(async () => {
                const c = await request<{ id: string }>(
                  "/conversations",
                  "POST",
                  {
                    person_id: value(f, "person"),
                    title: value(f, "title"),
                    external_conversation_id: value(f, "external"),
                  },
                );
                setSelected(c.id);
                setCreate(false);
              }, "Đã liên kết hội thoại");
            }}
          >
            <Field title="Liên hệ CRM">
              <select name="person" required>
                <option value="">Chọn liên hệ</option>
                {persons.data?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.display_name}
                  </option>
                ))}
              </select>
            </Field>
            <Field title="Tên hội thoại">
              <input name="title" required />
            </Field>
            <Field title="ID hoặc định danh hội thoại">
              <input name="external" required maxLength={128} />
            </Field>
            <button className="button" disabled={busy}>
              Liên kết
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}

function Preferences({
  version,
  act,
  busy,
  disconnect,
}: Common & { disconnect: () => void }) {
  const integrations = useData<Record<string, { configured: boolean }>>(
    "/integrations",
    version,
  );
  const backups = useData<
    { filename: string; size_bytes: number; created_at: string }[]
  >("/backup", version);
  const [provider, setProvider] = useState("threads"),
    [restore, setRestore] = useState<string | null>(null);
  return (
    <div className="two-columns">
      <section className="panel">
        <div className="section-heading">
          <h2>Kết nối nguồn chính thức</h2>
          <Wifi size={20} />
        </div>
        <DataState {...integrations} />
        {["facebook", "threads", "zalo"].map((p) => (
          <div className="list-row" key={p}>
            <div>
              <strong>
                {p === "zalo"
                  ? "Zalo OA"
                  : p === "threads"
                    ? "Threads"
                    : "Facebook Page"}
              </strong>
              <small>
                {integrations.data?.[p]?.configured
                  ? "Đã có token · cần quyền API phù hợp"
                  : "Chưa cấu hình access token"}
              </small>
            </div>
            <Badge tone={integrations.data?.[p]?.configured ? "green" : ""}>
              {integrations.data?.[p]?.configured
                ? "Đã cấu hình"
                : "Chưa kết nối"}
            </Badge>
            {integrations.data?.[p]?.configured && (
              <button
                className="icon-button"
                aria-label={`Xóa token ${p}`}
                disabled={busy}
                onClick={() =>
                  void act(
                    () => request(`/integrations/${p}/token`, "DELETE"),
                    "Đã xóa token lưu trong keyring",
                  )
                }
              >
                <X size={16} />
              </button>
            )}
          </div>
        ))}
        <form
          className="spaced"
          onSubmit={(e) => {
            e.preventDefault();
            const f = e.currentTarget;
            void act(async () => {
              await request(`/integrations/${provider}/token`, "PUT", {
                access_token: value(f, "token"),
              });
              f.reset();
            }, "Đã lưu token trong OS keyring");
          }}
        >
          <Field title="Nền tảng">
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              <option value="threads">Threads</option>
              <option value="facebook">Facebook Page</option>
              <option value="zalo">Zalo OA</option>
            </select>
          </Field>
          <Field title="Access token">
            <input
              name="token"
              type="password"
              autoComplete="off"
              minLength={10}
              required
            />
          </Field>
          <button className="button" disabled={busy}>
            Lưu kết nối
          </button>
        </form>
        <p className="muted spaced">
          Token được lưu trong kho thông tin xác thực của hệ điều hành. Facebook
          cần Page ID cấu hình trong engine. Trạng thái có token chưa xác nhận
          quyền API.
        </p>
        <button className="text-button" onClick={disconnect}>
          Đổi kết nối engine
          <ArrowRight size={15} />
        </button>
      </section>
      <section className="panel">
        <div className="section-heading">
          <h2>Dữ liệu & sao lưu</h2>
          <Database size={20} />
        </div>
        <p className="muted">
          Sao lưu SQLite nhất quán cả khi ứng dụng đang chạy. Xuất danh sách CRM
          để sử dụng trong bảng tính.
        </p>
        <div className="actions spaced">
          <button
            className="button"
            disabled={busy}
            onClick={() =>
              void act(
                () => request("/backup/create", "POST"),
                "Đã tạo bản sao lưu",
              )
            }
          >
            <Database size={16} />
            Tạo bản sao lưu
          </button>
          <button
            className="button secondary"
            disabled={busy}
            onClick={() =>
              void act(exportCustomers, "Đã xuất danh sách khách hàng")
            }
          >
            <Download size={16} />
            Xuất CSV
          </button>
        </div>
        <h3 className="spaced">Bản sao lưu trên máy</h3>
        <DataState {...backups} />
        {backups.data?.length ? (
          backups.data.map((b) => (
            <div className="backup-row" key={b.filename}>
              <div>
                <strong>{b.filename}</strong>
                <small>
                  {date(b.created_at)} · {(b.size_bytes / 1024).toFixed(0)} KB
                </small>
              </div>
              <button
                className="button secondary compact"
                onClick={() => setRestore(b.filename)}
              >
                Khôi phục
              </button>
            </div>
          ))
        ) : (
          <Empty
            title="Chưa có bản sao lưu"
            hint="Tạo bản đầu tiên để bảo vệ dữ liệu của bạn."
          />
        )}
        <div className="inset spaced">
          <h3>Lưu trữ dữ liệu</h3>
          <p className="muted">
            Bài quét thô mặc định được dọn sau 24 giờ. Bài đã lưu hoặc liên kết
            hồ sơ được bảo vệ. Token không nằm trong bản sao lưu CRM.
          </p>
        </div>
      </section>
      {restore && (
        <Modal title="Khôi phục dữ liệu" close={() => setRestore(null)}>
          <p>
            Bản sao lưu <strong>{restore}</strong> sẽ thay thế dữ liệu CRM hiện
            tại. Ứng dụng tạo thêm một bản sao lưu trước khi khôi phục.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void act(async () => {
                await request("/backup/restore", "POST", { filename: restore });
                setRestore(null);
              }, "Đã khôi phục dữ liệu");
            }}
          >
            <label className="checkbox">
              <input type="checkbox" required />
              Tôi xác nhận thay thế dữ liệu hiện tại.
            </label>
            <button className="button" disabled={busy}>
              Khôi phục bản sao lưu
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}

function Campaigns({ version, act, busy }: Common) {
  type Campaign = {
    id: string;
    name: string;
    status: string;
    message_template: string;
    frequency_cap_days: number;
  };
  type Recipient = {
    id: string;
    name: string;
    eligible: boolean;
    reason: string;
    status: string;
    content: string;
  };
  const campaigns = useData<Campaign[]>("/campaigns", version),
    customers = useData<Customer[]>("/customers?limit=500", version);
  const [selected, setSelected] = useState<string | null>(null),
    [create, setCreate] = useState(false),
    [review, setReview] = useState<Recipient | null>(null);
  const preview = useData<Recipient[]>(
    selected ? `/campaigns/${selected}/preview` : null,
    version,
  );
  const [reconcile, setReconcile] = useState<Recipient | null>(null);
  return (
    <>
      <div className="toolbar">
        <Badge tone="green">ZALO OA · TIN TƯ VẤN ĐƯỢC DUYỆT</Badge>
        <button className="button" onClick={() => setCreate(true)}>
          <Plus size={16} />
          Tạo đợt chăm sóc
        </button>
      </div>
      <p className="muted">
        Chỉ gửi qua OA chính thức tới khách đã đồng ý, có tương tác trong 7
        ngày. Giờ yên lặng: 20:00–08:00 Việt Nam. Mỗi tin cần được duyệt trước
        khi gửi.
      </p>
      <div className="two-columns spaced">
        <section className="panel">
          <h2>Đợt chăm sóc</h2>
          <DataState {...campaigns} />
          {campaigns.data?.length ? (
            campaigns.data.map((c) => (
              <button
                className={`conversation ${selected === c.id ? "selected" : ""}`}
                key={c.id}
                onClick={() => setSelected(c.id)}
              >
                <div>
                  <strong>{c.name}</strong>
                  <small>
                    {c.status} · Giới hạn {c.frequency_cap_days} ngày / tin
                  </small>
                </div>
                <ChevronRight size={15} />
              </button>
            ))
          ) : (
            <Empty
              title="Chưa có đợt chăm sóc"
              hint="Tạo bản nháp rồi kiểm tra quyền liên hệ từng khách hàng."
            />
          )}
        </section>
        <section className="panel">
          <h2>Kiểm tra & duyệt nội dung</h2>
          <DataState {...preview} />
          {preview.data?.length ? (
            preview.data.map((r) => (
              <div className="comment" key={r.id}>
                <div className="section-heading">
                  <strong>{r.name}</strong>
                  <Badge tone={r.eligible ? "green" : "warning"}>
                    {r.eligible
                      ? "Đủ điều kiện"
                      : r.status === "SENT"
                        ? "Đã gửi"
                        : "Chưa thể gửi"}
                  </Badge>
                </div>
                <p>{r.content}</p>
                <small>{r.reason}</small>
                <button
                  className="button secondary compact spaced"
                  disabled={!r.eligible || busy}
                  onClick={() => setReview(r)}
                >
                  Duyệt & gửi qua OA
                </button>
                {["UNKNOWN", "SENDING"].includes(r.status) && (
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() => setReconcile(r)}
                  >
                    Đối soát kết quả trong OA
                  </button>
                )}
              </div>
            ))
          ) : (
            <Empty
              title="Chọn một đợt chăm sóc"
              hint="Các điều kiện liên hệ được kiểm tra lại ngay trước khi gửi."
            />
          )}
        </section>
      </div>
      {create && (
        <Modal title="Tạo đợt chăm sóc OA" close={() => setCreate(false)}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = e.currentTarget;
              void act(async () => {
                const ids = new FormData(f).getAll("customer").map(String);
                const c = await request<{ id: string }>("/campaigns", "POST", {
                  name: value(f, "name"),
                  message_template: value(f, "template"),
                  customer_ids: ids,
                  frequency_cap_days: Number(value(f, "cap")),
                });
                setSelected(c.id);
                setCreate(false);
              }, "Đã tạo bản nháp chăm sóc");
            }}
          >
            <Field title="Tên đợt chăm sóc">
              <input name="name" required maxLength={255} />
            </Field>
            <Field title="Nội dung tư vấn (dùng {name} cho tên khách)">
              <textarea name="template" required rows={4} maxLength={2000} />
            </Field>
            <Field title="Khoảng cách tối thiểu giữa các tin (ngày)">
              <input
                name="cap"
                type="number"
                min="1"
                max="365"
                defaultValue="7"
                required
              />
            </Field>
            <h3>Chọn khách hàng (tối đa 100)</h3>
            {customers.data?.map((c) => (
              <label className="checkbox" key={c.id}>
                <input name="customer" type="checkbox" value={c.id} />
                {c.display_name}
              </label>
            ))}
            <button className="button" disabled={busy}>
              Tạo bản nháp
            </button>
          </form>
        </Modal>
      )}
      {review && (
        <Modal
          title="Duyệt tin nhắn gửi thật qua OA"
          close={() => setReview(null)}
        >
          <h3>Người nhận: {review.name}</h3>
          <p className="post-content">{review.content}</p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void act(async () => {
                const result = await request<{ status: string }>(
                  `/campaigns/${selected}/recipients/${review.id}/send`,
                  "POST",
                  { reviewed: true },
                );
                setReview(null);
                if (result.status !== "SENT")
                  throw new Error(
                    "OA từ chối gửi tin. Kiểm tra quyền và điều kiện OA.",
                  );
              }, "OA đã xác nhận gửi tin thành công");
            }}
          >
            <label className="checkbox">
              <input type="checkbox" required />
              Tôi đã kiểm tra người nhận, quyền liên hệ và nội dung.
            </label>
            <button className="button" disabled={busy}>
              <Send size={15} />
              Gửi qua Zalo OA
            </button>
          </form>
        </Modal>
      )}
      {reconcile && (
        <Modal
          title="Đối soát tin chưa xác nhận"
          close={() => setReconcile(null)}
        >
          <p>
            Kiểm tra lịch sử gửi trong OA trước khi xác nhận kết quả cho{" "}
            {reconcile.name}.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = e.currentTarget;
              void act(async () => {
                await request(
                  `/campaigns/${selected}/recipients/${reconcile.id}/reconcile`,
                  "PATCH",
                  {
                    delivered: value(f, "result") === "sent",
                    note: value(f, "note"),
                  },
                );
                setReconcile(null);
              }, "Đã ghi nhận kết quả đối soát");
            }}
          >
            <Field title="Kết quả trong OA">
              <select name="result">
                <option value="sent">OA xác nhận đã gửi</option>
                <option value="rejected">Xác nhận chưa gửi</option>
              </select>
            </Field>
            <Field title="Ghi chú đối soát">
              <textarea name="note" required rows={3} />
            </Field>
            <label className="checkbox">
              <input type="checkbox" required />
              Tôi đã kiểm tra lịch sử OA thực tế.
            </label>
            <button className="button" disabled={busy}>
              Lưu kết quả đối soát
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}
