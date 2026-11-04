import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Layout from "./components/Layout";
import { ContentProvider } from "./context/ContentContext";
import Home from "./pages/Home";
import LabPage from "./pages/LabPage";
import { About, Experience, ExperienceDetail, Expertise, CaseStudies, CaseStudyDetail, Certifications, Resume, Contact, Articles } from "./pages/Pages";
import { Automation, LabIndex, DemoTour } from "./pages/Automation";
import { Admin, AdminLogin } from "./pages/Admin";
import Tour from "./pages/Tour";
import GrcWorkspace from "./pages/GrcWorkspace";

function NotFound() {
  return <div className="mx-auto max-w-3xl px-5 py-24"><h1 className="font-heading text-3xl font-bold">Page not found</h1><a href="/" className="mt-4 inline-block text-teal-700">Return home</a></div>;
}

function App() {
  return (
    <ContentProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/about" element={<About />} />
            <Route path="/experience" element={<Experience />} />
            <Route path="/experience/:slug" element={<ExperienceDetail />} />
            <Route path="/expertise" element={<Expertise />} />
            <Route path="/lab" element={<LabIndex />} />
            <Route path="/lab/:key" element={<LabPage />} />
            <Route path="/agents" element={<LabPage forceKey="agents" />} />
            <Route path="/automation" element={<Automation />} />
            <Route path="/irm" element={<GrcWorkspace />} />
            <Route path="/tour" element={<Tour />} />
            <Route path="/demo" element={<DemoTour />} />
            <Route path="/case-studies" element={<CaseStudies />} />
            <Route path="/case-studies/:slug" element={<CaseStudyDetail />} />
            <Route path="/certifications" element={<Certifications />} />
            <Route path="/resume" element={<Resume />} />
            <Route path="/contact" element={<Contact />} />
            <Route path="/articles" element={<Articles />} />
            <Route path="/admin/login" element={<AdminLogin />} />
            <Route path="/admin" element={<Admin />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </ContentProvider>
  );
}

export default App;
