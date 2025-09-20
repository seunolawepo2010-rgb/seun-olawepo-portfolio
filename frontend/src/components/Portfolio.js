import React, { useState } from 'react';
import { ArrowRight, Download, Calendar, Mail, Linkedin, ExternalLink, Filter, ChevronDown, MapPin, Clock, DollarSign, Users, TrendingUp } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Separator } from './ui/separator';
import portfolioData from '../data/mock';

const Portfolio = () => {
  const [selectedFilter, setSelectedFilter] = useState('All');
  const [selectedProject, setSelectedProject] = useState(null);

  // Filter projects based on selected category
  const filteredProjects = selectedFilter === 'All' 
    ? portfolioData.projects 
    : portfolioData.projects.filter(project => 
        project.category === selectedFilter || project.tags.includes(selectedFilter)
      );

  const projectCategories = ['All', 'Agile Leadership', 'Product Management', 'Release Train Engineering', 'DevOps & Quality', 'Stakeholder Management', 'Agile Coaching'];

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="fixed top-0 w-full bg-white/90 backdrop-blur-md border-b border-gray-100 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <nav className="flex items-center justify-between">
            <div className="text-xl font-light text-gray-900">
              {portfolioData.hero.name}
            </div>
            <div className="hidden md:flex items-center space-x-8 text-sm text-gray-600">
              <a href="#about" className="hover:text-gray-900 transition-colors">About</a>
              <a href="#portfolio" className="hover:text-gray-900 transition-colors">Portfolio</a>
              <a href="#experience" className="hover:text-gray-900 transition-colors">Experience</a>
              <a href="#skills" className="hover:text-gray-900 transition-colors">Skills</a>
              <a href="#contact" className="hover:text-gray-900 transition-colors">Contact</a>
            </div>
            <Button size="sm" className="bg-gray-900 text-white hover:bg-gray-800">
              <Calendar className="w-4 h-4 mr-2" />
              Schedule Call
            </Button>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-24 pb-16 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="space-y-4">
                <h1 className="text-5xl md:text-6xl font-light text-gray-900 leading-tight tracking-tight">
                  {portfolioData.hero.shortTitle}
                </h1>
                <p className="text-xl text-gray-600 leading-relaxed">
                  {portfolioData.hero.bio}
                </p>
              </div>
              
              {/* Key Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                {portfolioData.about.keyStats.map((stat, index) => (
                  <div key={index} className="text-center">
                    <div className="text-2xl font-light text-gray-900">{stat.value}</div>
                    <div className="text-sm text-gray-600">{stat.label}</div>
                  </div>
                ))}
              </div>

              <div className="flex flex-col sm:flex-row gap-4">
                <Button size="lg" className="bg-gray-900 text-white hover:bg-gray-800">
                  {portfolioData.hero.primaryCTA}
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
                <Button size="lg" variant="outline">
                  <Download className="w-4 h-4 mr-2" />
                  {portfolioData.hero.secondaryCTA}
                </Button>
              </div>
            </div>
            
            <div className="flex justify-center">
              <div className="w-80 h-80 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
                <div className="w-72 h-72 rounded-full bg-white shadow-lg flex items-center justify-center">
                  <div className="text-6xl text-gray-400">👤</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* About Section */}
      <section id="about" className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-6">
          <div className="space-y-8">
            <div className="text-center space-y-4">
              <h2 className="text-3xl font-light text-gray-900">About</h2>
              <p className="text-lg text-gray-600 leading-relaxed">
                {portfolioData.about.long}
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
                <div className="text-xl font-light text-gray-900">20+ Teams</div>
                <div className="text-sm text-gray-600">Mentored & Led</div>
              </div>
              <div className="text-center space-y-2">
                <TrendingUp className="w-8 h-8 text-gray-600 mx-auto" />
                <div className="text-xl font-light text-gray-900">35% Improvement</div>
                <div className="text-sm text-gray-600">Delivery Performance</div>
              </div>
            </div>
          </div>
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
                  onClick={() => setSelectedFilter(category)}
                  className={selectedFilter === category ? "bg-gray-900 text-white" : ""}
                >
                  {category}
                </Button>
              ))}
            </div>

            {/* Projects Grid */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {filteredProjects.map((project) => (
                <Card key={project.id} className="group cursor-pointer hover:shadow-lg transition-all duration-300">
                  <div className="aspect-video bg-gradient-to-br from-gray-100 to-gray-200 rounded-t-lg overflow-hidden">
                    <div className="w-full h-full flex items-center justify-center text-gray-400 text-4xl">
                      📊
                    </div>
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
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
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

            <div className="space-y-8">
              {portfolioData.experience.map((exp, index) => (
                <Card key={exp.id} className="p-6">
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

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {Object.entries(portfolioData.skills).map(([category, skills]) => (
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

            <Tabs defaultValue="certifications" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="certifications">Certifications</TabsTrigger>
                <TabsTrigger value="education">Education</TabsTrigger>
              </TabsList>
              
              <TabsContent value="certifications" className="mt-8">
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {portfolioData.certifications.map((cert, index) => (
                    <Card key={index} className="p-4">
                      <CardContent className="p-0">
                        <div className="space-y-2">
                          <div className="text-sm font-medium text-gray-900">{cert.name}</div>
                          <div className="text-sm text-gray-600">{cert.issuer}</div>
                          <div className="flex justify-between items-center">
                            <Badge variant="outline" className="text-xs">{cert.year}</Badge>
                            <div className="text-xs text-gray-500">{cert.credentialId}</div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>
              
              <TabsContent value="education" className="mt-8">
                <div className="grid md:grid-cols-2 gap-6">
                  {portfolioData.education.map((edu, index) => (
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
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section id="contact" className="py-16">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <div className="space-y-8">
            <div className="space-y-4">
              <h2 className="text-3xl font-light text-gray-900">Let's Connect</h2>
              <p className="text-lg text-gray-600">{portfolioData.contact.location}</p>
              <div className="text-sm text-gray-500">{portfolioData.contact.cta}</div>
            </div>

            <div className="flex flex-col sm:flex-row justify-center gap-4">
              <Button size="lg" className="bg-gray-900 text-white hover:bg-gray-800">
                <Calendar className="w-4 h-4 mr-2" />
                Schedule Meeting
              </Button>
              <Button size="lg" variant="outline">
                <Linkedin className="w-4 h-4 mr-2" />
                LinkedIn Profile
              </Button>
              <Button size="lg" variant="outline">
                <Mail className="w-4 h-4 mr-2" />
                Send Email
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-gray-100">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <div className="text-sm text-gray-600">
              © 2025 {portfolioData.hero.name} — All rights reserved.
            </div>
            <div className="flex items-center space-x-6">
              <a href={portfolioData.contact.linkedin} className="text-gray-400 hover:text-gray-600 transition-colors">
                <Linkedin className="w-5 h-5" />
              </a>
              <a href={`mailto:${portfolioData.contact.email}`} className="text-gray-400 hover:text-gray-600 transition-colors">
                <Mail className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Portfolio;