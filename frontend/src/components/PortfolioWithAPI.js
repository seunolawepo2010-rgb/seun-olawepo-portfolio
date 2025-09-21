import React, { useState, useEffect } from 'react';
import { ArrowRight, Download, Calendar, Mail, Linkedin, ExternalLink, Filter, ChevronDown, MapPin, Clock, DollarSign, Users, TrendingUp, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Separator } from './ui/separator';
import { Dialog, DialogContent, DialogTrigger } from './ui/dialog';
import { Alert, AlertDescription } from './ui/alert';
import ContactForm from './ContactForm';
import { portfolioAPI, contactAPI, handleApiError } from '../services/api';

const LoadingSpinner = ({ text = "Loading..." }) => (
  <div className="flex items-center justify-center py-12">
    <Loader2 className="w-6 h-6 animate-spin mr-2" />
    <span className="text-gray-600">{text}</span>
  </div>
);

const ErrorMessage = ({ message, onRetry }) => (
  <Alert variant="destructive" className="my-4">
    <AlertCircle className="h-4 w-4" />
    <AlertDescription className="flex items-center justify-between">
      <span>{message}</span>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </AlertDescription>
  </Alert>
);

const Portfolio = () => {
  // State management
  const [heroData, setHeroData] = useState(null);
  const [aboutData, setAboutData] = useState(null);
  const [projectsData, setProjectsData] = useState({ projects: [], total: 0, filtered: 0 });
  const [experienceData, setExperienceData] = useState([]);
  const [skillsData, setSkillsData] = useState({ skills: {} });
  const [certificationsData, setCertificationsData] = useState({ certifications: [], education: [] });
  const [contactData, setContactData] = useState(null);
  
  // Loading states
  const [loadingStates, setLoadingStates] = useState({
    hero: true,
    about: true,
    projects: true,
    experience: true,
    skills: true,
    certifications: true,
    contact: true
  });
  
  // Error states
  const [errors, setErrors] = useState({});
  
  // UI states
  const [selectedFilter, setSelectedFilter] = useState('All');
  const [showContactForm, setShowContactForm] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [contactFormData, setContactFormData] = useState({});

  // Helper function to update loading state
  const setLoading = (section, isLoading) => {
    setLoadingStates(prev => ({ ...prev, [section]: isLoading }));
  };

  // Helper function to set error
  const setError = (section, error) => {
    setErrors(prev => ({ ...prev, [section]: error }));
    setLoading(section, false);
  };

  // API call functions
  const loadHeroData = async () => {
    try {
      setLoading('hero', true);
      const data = await portfolioAPI.getHero();
      setHeroData(data);
      setErrors(prev => ({ ...prev, hero: null }));
    } catch (error) {
      setError('hero', handleApiError(error));
    } finally {
      setLoading('hero', false);
    }
  };

  const loadAboutData = async () => {
    try {
      setLoading('about', true);
      const data = await portfolioAPI.getAbout();
      setAboutData(data);
      setErrors(prev => ({ ...prev, about: null }));
    } catch (error) {
      setError('about', handleApiError(error));
    } finally {
      setLoading('about', false);
    }
  };

  const loadProjectsData = async (filters = {}) => {
    try {
      setLoading('projects', true);
      const data = await portfolioAPI.getProjects(filters);
      setProjectsData(data);
      setErrors(prev => ({ ...prev, projects: null }));
    } catch (error) {
      setError('projects', handleApiError(error));
    } finally {
      setLoading('projects', false);
    }
  };

  const loadExperienceData = async () => {
    try {
      setLoading('experience', true);
      const data = await portfolioAPI.getExperience();
      setExperienceData(data);
      setErrors(prev => ({ ...prev, experience: null }));
    } catch (error) {
      setError('experience', handleApiError(error));
    } finally {
      setLoading('experience', false);
    }
  };

  const loadSkillsData = async () => {
    try {
      setLoading('skills', true);
      const data = await portfolioAPI.getSkills();
      setSkillsData(data);
      setErrors(prev => ({ ...prev, skills: null }));
    } catch (error) {
      setError('skills', handleApiError(error));
    } finally {
      setLoading('skills', false);
    }
  };

  const loadCertificationsData = async () => {
    try {
      setLoading('certifications', true);
      const data = await portfolioAPI.getCertifications();
      setCertificationsData(data);
      setErrors(prev => ({ ...prev, certifications: null }));
    } catch (error) {
      setError('certifications', handleApiError(error));
    } finally {
      setLoading('certifications', false);
    }
  };

  const loadContactData = async () => {
    try {
      setLoading('contact', true);
      const data = await contactAPI.getContactInfo();
      setContactData(data);
      setErrors(prev => ({ ...prev, contact: null }));
    } catch (error) {
      setError('contact', handleApiError(error));
    } finally {
      setLoading('contact', false);
    }
  };

  // Initial data loading
  useEffect(() => {
    loadHeroData();
    loadAboutData();
    loadProjectsData();
    loadExperienceData();
    loadSkillsData();
    loadCertificationsData();
    loadContactData();
  }, []);

  // Handle project filtering
  const handleFilterChange = (newFilter) => {
    setSelectedFilter(newFilter);
    const filters = newFilter === 'All' ? {} : { category: newFilter };
    loadProjectsData(filters);
  };

  // Handle project card click
  const handleProjectClick = (project) => {
    setSelectedProject(project);
    setShowProjectModal(true);
  };

  // Handle project discussion - opens contact form with pre-filled subject
  const handleProjectDiscussion = (project) => {
    setShowProjectModal(false);
    // Pre-fill contact form with project information
    const preFilledData = {
      subject: `Discussion: ${project.title}`,
      message: `Hi Seun,\n\nI'm interested in discussing your "${project.title}" case study. I'd like to learn more about:\n\n- The implementation approach\n- Key challenges and solutions\n- Potential application to my organization\n\nLooking forward to our conversation.\n\nBest regards,`
    };
    setContactFormData(preFilledData);
    setTimeout(() => setShowContactForm(true), 300);
  };

  const projectCategories = ['All', 'AI/ML Solutions', 'Agile Leadership', 'Product Management', 'Release Train Engineering', 'DevOps & Quality', 'Stakeholder Management', 'Agile Coaching'];

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="fixed top-0 w-full bg-white/90 backdrop-blur-md border-b border-gray-100 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <nav className="flex items-center justify-between">
            <div className="text-xl font-light text-gray-900">
              {heroData?.name || "Seun M. Olawepo"}
            </div>
            <div className="hidden md:flex items-center space-x-8 text-sm text-gray-600">
              <a href="#about" className="hover:text-gray-900 transition-colors">About</a>
              <a href="#portfolio" className="hover:text-gray-900 transition-colors">Portfolio</a>
              <a href="#experience" className="hover:text-gray-900 transition-colors">Experience</a>
              <a href="#skills" className="hover:text-gray-900 transition-colors">Skills</a>
              <a href="#contact" className="hover:text-gray-900 transition-colors">Contact</a>
            </div>
            <Dialog open={showContactForm} onOpenChange={setShowContactForm}>
              <DialogTrigger asChild>
                <Button size="sm" className="bg-gray-900 text-white hover:bg-gray-800">
                  <Calendar className="w-4 h-4 mr-2" />
                  Schedule Call
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[500px]">
                <ContactForm onClose={() => {
                  setShowContactForm(false);
                  setContactFormData({});
                }} preFilledData={contactFormData} />
              </DialogContent>
            </Dialog>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-24 pb-16 px-6">
        <div className="max-w-7xl mx-auto">
          {loadingStates.hero ? (
            <LoadingSpinner text="Loading hero section..." />
          ) : errors.hero ? (
            <ErrorMessage message={errors.hero} onRetry={loadHeroData} />
          ) : heroData ? (
            <div className="grid md:grid-cols-2 gap-12 items-center">
              <div className="space-y-8">
                <div className="space-y-4">
                  <h1 className="text-5xl md:text-6xl font-light text-gray-900 leading-tight tracking-tight">
                    {heroData.short_title}
                  </h1>
                  <p className="text-xl text-gray-600 leading-relaxed">
                    {heroData.bio}
                  </p>
                </div>
                
                {/* Key Stats */}
                {aboutData?.key_stats && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                    {aboutData.key_stats.map((stat, index) => (
                      <div key={index} className="text-center">
                        <div className="text-2xl font-light text-gray-900">{stat.value}</div>
                        <div className="text-sm text-gray-600">{stat.label}</div>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex flex-col sm:flex-row gap-4">
                  <Button size="lg" className="bg-gray-900 text-white hover:bg-gray-800">
                    {heroData.primary_cta}
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                  <Button size="lg" variant="outline">
                    <Download className="w-4 h-4 mr-2" />
                    {heroData.secondary_cta}
                  </Button>
                </div>
              </div>
              
              <div className="flex justify-center">
                <div className="w-80 h-80 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center overflow-hidden">
                  <img 
                    src={heroData.image} 
                    alt={`${heroData.name} - Professional Portrait`}
                    className="w-full h-full object-cover rounded-full"
                    onError={(e) => {
                      // Fallback to placeholder if image fails to load
                      e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='320' viewBox='0 0 320 320'%3E%3Crect width='320' height='320' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%236b7280' font-size='48'%3E👤%3C/text%3E%3C/svg%3E";
                    }}
                  />
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </section>

      {/* About Section */}
      <section id="about" className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-6">
          {loadingStates.about ? (
            <LoadingSpinner text="Loading about section..." />
          ) : errors.about ? (
            <ErrorMessage message={errors.about} onRetry={loadAboutData} />
          ) : aboutData ? (
            <div className="space-y-8">
              <div className="text-center space-y-4">
                <h2 className="text-3xl font-light text-gray-900">About</h2>
                <p className="text-lg text-gray-600 leading-relaxed">
                  {aboutData.long}
                </p>
              </div>
              
              <div className="grid md:grid-cols-3 gap-8">
                <div className="text-center space-y-2">
                  <DollarSign className="w-8 h-8 text-gray-600 mx-auto" />
                  <div className="text-xl font-light text-gray-900">$5M+ Managed</div>
                  <div className="text-sm text-gray-600">Project Budgets</div>
                </div>
                <div className="text-center space-y-2">
                  <Users className="w-8 h-8 text-gray-600 mx-auto" />
                  <div className="text-xl font-light text-gray-900">200+ Teams</div>
                  <div className="text-sm text-gray-600">Mentored & Led</div>
                </div>
                <div className="text-center space-y-2">
                  <TrendingUp className="w-8 h-8 text-gray-600 mx-auto" />
                  <div className="text-xl font-light text-gray-900">35% Improvement</div>
                  <div className="text-sm text-gray-600">Delivery Performance</div>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </section>

      {/* Portfolio Section */}
      <section id="portfolio" className="py-16">
        <div className="max-w-7xl mx-auto px-6">
          <div className="space-y-12">
            <div className="text-center space-y-4">
              <h2 className="text-3xl font-light text-gray-900">Case Studies</h2>
              <p className="text-lg text-gray-600">
                Transforming organizations through Agile leadership and strategic delivery
              </p>
            </div>

            {/* Project Filters */}
            <div className="flex flex-wrap justify-center gap-2">
              {projectCategories.map((category) => (
                <Button
                  key={category}
                  variant={selectedFilter === category ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleFilterChange(category)}
                  className={selectedFilter === category ? "bg-gray-900 text-white" : ""}
                  disabled={loadingStates.projects}
                >
                  {category}
                </Button>
              ))}
            </div>

            {/* Projects Grid */}
            {loadingStates.projects ? (
              <LoadingSpinner text="Loading projects..." />
            ) : errors.projects ? (
              <ErrorMessage message={errors.projects} onRetry={() => loadProjectsData()} />
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                {projectsData.projects.map((project) => (
                  <Card key={project.id} className="group cursor-pointer hover:shadow-lg transition-all duration-300" onClick={() => handleProjectClick(project)}>
                    <div className="aspect-video bg-gradient-to-br from-gray-100 to-gray-200 rounded-t-lg overflow-hidden">
                      <img 
                        src={project.image} 
                        alt={project.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        onError={(e) => {
                          e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'%3E%3Crect width='400' height='300' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%236b7280' font-size='24'%3E📊 Case Study%3C/text%3E%3C/svg%3E";
                        }}
                      />
                    </div>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <Badge variant="outline" className="mb-2">{project.category}</Badge>
                        <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
                      </div>
                      <CardTitle className="text-lg font-medium group-hover:text-gray-600 transition-colors">
                        {project.title}
                      </CardTitle>
                      <CardDescription className="text-sm text-gray-600 line-clamp-2">
                        {project.problem}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          {Object.entries(project.metrics).slice(0, 2).map(([key, value]) => (
                            <div key={key} className="text-center p-2 bg-gray-50 rounded">
                              <div className="font-medium text-gray-900">{value}</div>
                              <div className="text-gray-600 capitalize">{key.replace('_', ' ')}</div>
                            </div>
                          ))}
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {project.tags.slice(0, 3).map((tag) => (
                            <Badge key={tag} variant="secondary" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                        <div className="text-xs text-gray-500 text-center pt-2 border-t">
                          Click to view detailed case study
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Experience Section */}
      <section id="experience" className="py-16 bg-gray-50">
        <div className="max-w-6xl mx-auto px-6">
          <div className="space-y-12">
            <div className="text-center space-y-4">
              <h2 className="text-3xl font-light text-gray-900">Experience</h2>
              <p className="text-lg text-gray-600">15+ years of Agile leadership across Fortune 500 companies</p>
            </div>

            {loadingStates.experience ? (
              <LoadingSpinner text="Loading experience..." />
            ) : errors.experience ? (
              <ErrorMessage message={errors.experience} onRetry={loadExperienceData} />
            ) : (
              <div className="space-y-8">
                {experienceData.map((exp, index) => (
                  <Card key={exp.id || index} className="p-6">
                    <div className="grid md:grid-cols-4 gap-6">
                      <div className="md:col-span-1 space-y-2">
                        <div className="text-sm text-gray-600 flex items-center">
                          <Clock className="w-4 h-4 mr-1" />
                          {exp.period}
                        </div>
                        <div className="text-sm text-gray-600 flex items-center">
                          <MapPin className="w-4 h-4 mr-1" />
                          {exp.location || exp.company}
                        </div>
                      </div>
                      
                      <div className="md:col-span-3 space-y-4">
                        <div>
                          <h3 className="text-xl font-medium text-gray-900">{exp.role}</h3>
                          <div className="text-lg text-gray-600">{exp.company}</div>
                        </div>
                        
                        <ul className="space-y-2">
                          {exp.achievements.map((achievement, achIndex) => (
                            <li key={achIndex} className="text-gray-700 flex items-start">
                              <div className="w-2 h-2 bg-gray-400 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                              {achievement}
                            </li>
                          ))}
                        </ul>
                        
                        <div className="flex flex-wrap gap-2">
                          {exp.tags.map((tag) => (
                            <Badge key={tag} variant="outline" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Skills Section */}
      <section id="skills" className="py-16">
        <div className="max-w-6xl mx-auto px-6">
          <div className="space-y-12">
            <div className="text-center space-y-4">
              <h2 className="text-3xl font-light text-gray-900">Skills & Expertise</h2>
              <p className="text-lg text-gray-600">Core competencies in Agile leadership and enterprise delivery</p>
            </div>

            {loadingStates.skills ? (
              <LoadingSpinner text="Loading skills..." />
            ) : errors.skills ? (
              <ErrorMessage message={errors.skills} onRetry={loadSkillsData} />
            ) : (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                {Object.entries(skillsData.skills).map(([category, skills]) => (
                  <Card key={category} className="p-6">
                    <CardHeader className="p-0 pb-4">
                      <CardTitle className="text-lg font-medium text-gray-900">
                        {category}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="space-y-2">
                        {skills.map((skill) => (
                          <Badge key={skill} variant="secondary" className="text-xs mr-1 mb-1">
                            {skill}
                          </Badge>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Certifications Section */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-6xl mx-auto px-6">
          <div className="space-y-12">
            <div className="text-center space-y-4">
              <h2 className="text-3xl font-light text-gray-900">Certifications & Education</h2>
              <p className="text-lg text-gray-600">Professional credentials and academic foundation</p>
            </div>

            {loadingStates.certifications ? (
              <LoadingSpinner text="Loading certifications..." />
            ) : errors.certifications ? (
              <ErrorMessage message={errors.certifications} onRetry={loadCertificationsData} />
            ) : (
              <Tabs defaultValue="certifications" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="certifications">Certifications</TabsTrigger>
                  <TabsTrigger value="education">Education</TabsTrigger>
                </TabsList>
                
                <TabsContent value="certifications" className="mt-8">
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {certificationsData.certifications.map((cert, index) => (
                      <Card key={index} className="p-4">
                        <CardContent className="p-0">
                          <div className="space-y-2">
                            <div className="text-sm font-medium text-gray-900">{cert.name}</div>
                            <div className="text-sm text-gray-600">{cert.issuer}</div>
                            <div className="flex justify-between items-center">
                              <Badge variant="outline" className="text-xs">{cert.year}</Badge>
                              <div className="text-xs text-gray-500">{cert.credential_id}</div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </TabsContent>
                
                <TabsContent value="education" className="mt-8">
                  <div className="grid md:grid-cols-2 gap-6">
                    {certificationsData.education.map((edu, index) => (
                      <Card key={index} className="p-6">
                        <CardContent className="p-0">
                          <div className="space-y-3">
                            <div>
                              <div className="text-lg font-medium text-gray-900">{edu.degree}</div>
                              <div className="text-gray-600">{edu.field}</div>
                            </div>
                            <div>
                              <div className="text-sm text-gray-600">{edu.institution}</div>
                              <div className="text-sm text-gray-500">{edu.location} • {edu.year}</div>
                            </div>
                            <div className="text-sm text-gray-600">{edu.details}</div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </TabsContent>
              </Tabs>
            )}
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section id="contact" className="py-16">
        <div className="max-w-4xl mx-auto px-6 text-center">
          {loadingStates.contact ? (
            <LoadingSpinner text="Loading contact info..." />
          ) : errors.contact ? (
            <ErrorMessage message={errors.contact} onRetry={loadContactData} />
          ) : contactData ? (
            <div className="space-y-8">
              <div className="space-y-4">
                <h2 className="text-3xl font-light text-gray-900">Let's Connect</h2>
                <p className="text-lg text-gray-600">{contactData.location}</p>
                <div className="text-sm text-gray-500">{contactData.availability}</div>
                <div className="text-sm text-gray-500">{contactData.cta}</div>
              </div>

              <div className="flex flex-col sm:flex-row justify-center gap-4">
                <Dialog open={showContactForm} onOpenChange={setShowContactForm}>
                  <DialogTrigger asChild>
                    <Button size="lg" className="bg-gray-900 text-white hover:bg-gray-800">
                      <Calendar className="w-4 h-4 mr-2" />
                      Schedule Meeting
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-[500px]">
                    <ContactForm onClose={() => {
                      setShowContactForm(false);
                      setContactFormData({});
                    }} preFilledData={contactFormData} />
                  </DialogContent>
                </Dialog>
                
                <Button size="lg" variant="outline" asChild>
                  <a href={contactData.linkedin} target="_blank" rel="noopener noreferrer">
                    <Linkedin className="w-4 h-4 mr-2" />
                    LinkedIn Profile
                  </a>
                </Button>
                
                <Button size="lg" variant="outline" asChild>
                  <a href={`mailto:${contactData.email}`}>
                    <Mail className="w-4 h-4 mr-2" />
                    Send Email
                  </a>
                </Button>
              </div>
            </div>
          ) : null}
        </div>
      </section>
      
      {/* Project Detail Modal */}
      <Dialog open={showProjectModal} onOpenChange={setShowProjectModal}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          {selectedProject && (
            <div className="space-y-6">
              {/* Header */}
              <div className="space-y-4">
                <div className="flex items-start justify-between">
                  <Badge variant="outline">{selectedProject.category}</Badge>
                  <div className="text-sm text-gray-500">{selectedProject.tags.find(tag => tag.match(/\d{4}/))}</div>
                </div>
                <h2 className="text-2xl font-bold text-gray-900">{selectedProject.title}</h2>
                <p className="text-gray-600">{selectedProject.role}</p>
              </div>

              {/* Project Image */}
              <div className="aspect-video bg-gradient-to-br from-gray-100 to-gray-200 rounded-lg overflow-hidden">
                <img 
                  src={selectedProject.image} 
                  alt={selectedProject.title}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='600' height='400' viewBox='0 0 600 400'%3E%3Crect width='600' height='400' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%236b7280' font-size='24'%3E📊 {selectedProject.title}%3C/text%3E%3C/svg%3E";
                  }}
                />
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(selectedProject.metrics).map(([key, value]) => (
                  <div key={key} className="text-center p-3 bg-gray-50 rounded-lg">
                    <div className="text-xl font-bold text-gray-900">{value}</div>
                    <div className="text-sm text-gray-600 capitalize">{key.replace('_', ' ')}</div>
                  </div>
                ))}
              </div>

              {/* Problem Statement */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <AlertCircle className="w-5 h-5 mr-2 text-red-500" />
                  Challenge & Context
                </h3>
                <p className="text-gray-700 leading-relaxed">{selectedProject.problem}</p>
              </div>

              {/* Approach */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <CheckCircle className="w-5 h-5 mr-2 text-blue-500" />
                  Strategic Approach
                </h3>
                <ul className="space-y-2">
                  {selectedProject.approach.map((item, index) => (
                    <li key={index} className="flex items-start">
                      <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                      <span className="text-gray-700">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Outcomes */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <TrendingUp className="w-5 h-5 mr-2 text-green-500" />
                  Results & Impact
                </h3>
                <ul className="space-y-2">
                  {selectedProject.outcomes.map((outcome, index) => (
                    <li key={index} className="flex items-start">
                      <div className="w-2 h-2 bg-green-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                      <span className="text-gray-700">{outcome}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Artifacts */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <Download className="w-5 h-5 mr-2 text-purple-500" />
                  Deliverables & Artifacts
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {selectedProject.artifacts.map((artifact, index) => (
                    <div key={index} className="flex items-center p-2 bg-gray-50 rounded">
                      <div className="w-2 h-2 bg-purple-500 rounded-full mr-3"></div>
                      <span className="text-sm text-gray-700">{artifact}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Tags */}
              <div className="space-y-3">
                <h3 className="text-lg font-semibold text-gray-900">Technologies & Methods</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedProject.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-sm">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4 border-t">
                <Button 
                  className="bg-gray-900 text-white hover:bg-gray-800"
                  onClick={() => handleProjectDiscussion(selectedProject)}
                >
                  <Mail className="w-4 h-4 mr-2" />
                  Discuss This Project
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => {
                    // Filter to show similar projects in the same category
                    setShowProjectModal(false);
                    setTimeout(() => {
                      handleFilterChange(selectedProject.category);
                      document.getElementById('portfolio')?.scrollIntoView({ behavior: 'smooth' });
                    }, 300);
                  }}
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  View Similar Work
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Footer */}
      <footer className="py-8 border-t border-gray-100">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <div className="text-sm text-gray-600">
              © 2025 {heroData?.name || "Seun M. Olawepo"} — All rights reserved.
            </div>
            <div className="flex items-center space-x-6">
              {contactData && (
                <>
                  <a href={contactData.linkedin} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-gray-600 transition-colors">
                    <Linkedin className="w-5 h-5" />
                  </a>
                  <a href={`mailto:${contactData.email}`} className="text-gray-400 hover:text-gray-600 transition-colors">
                    <Mail className="w-5 h-5" />
                  </a>
                </>
              )}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Portfolio;