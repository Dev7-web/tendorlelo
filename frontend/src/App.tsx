import { Route, Routes } from "react-router-dom";

import Layout from "@/components/layout/Layout";
import Companies from "@/pages/Companies";
import CompanyDetail from "@/pages/CompanyDetail";
import Dashboard from "@/pages/Dashboard";
import Jobs from "@/pages/Jobs";
import Search from "@/pages/Search";
import Settings from "@/pages/Settings";
import TenderDetail from "@/pages/TenderDetail";
import Tenders from "@/pages/Tenders";

const App = () => {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/tenders" element={<Tenders />} />
        <Route path="/tenders/:id" element={<TenderDetail />} />
        <Route path="/companies" element={<Companies />} />
        <Route path="/companies/:id" element={<CompanyDetail />} />
        <Route path="/search" element={<Search />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  );
};

export default App;
